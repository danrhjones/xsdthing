# Prompt: Recreate sample XSDs with include

Use with: Read `prompts/00-project-brief.md` first.

## Task

Create a minimal set of XSDs that demonstrate **xs:include** (one schema including another in the same namespace).

1. **ctypes.xsd** (or common.xsd)
   - Same `targetNamespace` as the main schema (e.g. `http://ncts.dgtaxud.ec` or `http://example.org/common`).
   - Define at least one **complexType** (e.g. `AddressType`, `PersonType`) with elements that have **default** values for sample data.
   - Define global **xs:element** declarations (e.g. `address`, `person`) that use those types.
   - If the main schema expects them, also define: a **xs:group** (e.g. `MESSAGE` with empty sequence), **xs:simpleType** (e.g. `phaseIDtype`), and complexTypes referenced by the main schema (e.g. `TransitOperationType01`, `CustomsOfficeOfDepartureType03`, `HolderOfTheTransitProcedureType20`).

2. **htypes.xsd**
   - Same `targetNamespace`; can be empty or a placeholder so the main schema’s `xs:include schemaLocation="htypes.xsd"` resolves.

3. **order.xsd** (main schema)
   - `xs:include schemaLocation="ctypes.xsd"` and `xs:include schemaLocation="htypes.xsd"`.
   - One global **xs:element** as root (e.g. `CC004C` of type `CC004CType`).
   - **xs:complexType** for the root with `xs:sequence` containing: `xs:group ref="MESSAGE"`, and xs:elements that use types defined in ctypes (e.g. `TransitOperation`, `CustomsOfficeOfDeparture`, `HolderOfTheTransitProcedure`), plus optional `xs:attribute` (e.g. `PhaseID` type `phaseIDtype`).

**Important:** Use **qualified type references** (e.g. `type="common:PersonType"` or `type="t:AddressType"`) in the main/included schemas so validators resolve types in the correct namespace. Ensure the generated XML validates with `xmllint --noout --schema order.xsd <generated.xml>`.
