from dataclasses import dataclass


@dataclass(frozen=True)
class DemoTenantSpec:
    name: str
    slug: str
    description: str
    short_label: str


DEMO_TENANTS: tuple[DemoTenantSpec, ...] = (
    DemoTenantSpec(
        name="Atlas Manufacturing",
        slug="atlas-manufacturing",
        description=(
            "Industrial manufacturing facility with hydraulic presses, CNC "
            "machines, assembly equipment, and robotic welding cells."
        ),
        short_label="Manufacturing",
    ),
    DemoTenantSpec(
        name="Borealis Cold Chain",
        slug="borealis-cold-chain",
        description=(
            "Cold-storage and logistics operation with chillers, freezers, "
            "loading docks, temperature monitoring, and refrigeration equipment."
        ),
        short_label="Cold-chain logistics",
    ),
    DemoTenantSpec(
        name="Helios Energy Services",
        slug="helios-energy-services",
        description=(
            "Renewable-energy operations company maintaining wind turbines, "
            "power inverters, transformers, and field equipment."
        ),
        short_label="Renewable energy",
    ),
)

DEMO_TENANT_NAMES: frozenset[str] = frozenset(spec.name for spec in DEMO_TENANTS)
