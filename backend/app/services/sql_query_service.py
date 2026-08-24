from uuid import UUID

from sqlalchemy import text
from sqlglot import exp, parse

from app.db.session import SessionLocal


class UnsafeSQLQueryError(ValueError):
    pass


ALLOWED_TABLES = {
    "assets",
    "maintenance_records",
    "maintenance_tickets",
}


def _get_tenant_scopes(
    where: exp.Expression,
) -> tuple[set[str], bool]:
    scoped_aliases: set[str] = set()
    has_unqualified_tenant_scope = False

    for equality in where.find_all(exp.EQ):
        left = equality.this
        right = equality.expression

        column = None
        placeholder = None

        if isinstance(left, exp.Column) and isinstance(right, exp.Placeholder):
            column = left
            placeholder = right

        elif isinstance(right, exp.Column) and isinstance(left, exp.Placeholder):
            column = right
            placeholder = left

        if column is None or placeholder is None:
            continue

        if column.name.lower() != "tenant_id":
            continue

        if placeholder.name != "tenant_id":
            continue

        if column.table:
            scoped_aliases.add(column.table.lower())
        else:
            has_unqualified_tenant_scope = True

    return scoped_aliases, has_unqualified_tenant_scope


def validate_readonly_sql(sql: str) -> None:
    statements = parse(
        sql,
        read="postgres",
    )

    if len(statements) != 1:
        raise UnsafeSQLQueryError("Exactly one SQL statement is allowed.")

    statement = statements[0]

    if not isinstance(statement, exp.Select):
        raise UnsafeSQLQueryError("Only SELECT queries are allowed.")

    tables = list(statement.find_all(exp.Table))

    if not tables:
        raise UnsafeSQLQueryError("Query must reference at least one table.")

    table_names = {table.name for table in tables}

    disallowed_tables = table_names - ALLOWED_TABLES

    if disallowed_tables:
        raise UnsafeSQLQueryError(f"Disallowed tables: {sorted(disallowed_tables)}")

    where = statement.args.get("where")

    if where is None:
        raise UnsafeSQLQueryError("Tenant-scoped queries must contain a WHERE clause.")

    if any(where.find_all(exp.Or)):
        raise UnsafeSQLQueryError("OR conditions are not allowed in tenant-scoped queries.")

    placeholders = list(where.find_all(exp.Placeholder))

    if not any(placeholder.name == "tenant_id" for placeholder in placeholders):
        raise UnsafeSQLQueryError("tenant_id must use the :tenant_id bind parameter.")

    scoped_aliases, has_unqualified_tenant_scope = _get_tenant_scopes(where)

    table_aliases = {table.alias_or_name.lower() for table in tables}

    if len(tables) == 1:
        table_alias = next(iter(table_aliases))

        if not has_unqualified_tenant_scope and table_alias not in scoped_aliases:
            raise UnsafeSQLQueryError("Query must be scoped by tenant_id.")

    else:
        missing_aliases = table_aliases - scoped_aliases

        if missing_aliases:
            raise UnsafeSQLQueryError(
                "Every table in a join must be tenant scoped. "
                f"Missing tenant filter for: {sorted(missing_aliases)}"
            )


async def execute_readonly_sql(
    tenant_id: UUID,
    sql: str,
    max_rows: int = 100,
) -> list[dict]:
    validate_readonly_sql(sql)

    clean_sql = sql.strip().rstrip(";")

    limited_sql = f"""
    SELECT *
    FROM (
        {clean_sql}
    ) AS safe_query
    LIMIT :max_rows
    """

    async with SessionLocal() as session:
        await session.execute(text("SET TRANSACTION READ ONLY"))

        result = await session.execute(
            text(limited_sql),
            {
                "tenant_id": tenant_id,
                "max_rows": max_rows,
            },
        )

        return [dict(row) for row in result.mappings().all()]
