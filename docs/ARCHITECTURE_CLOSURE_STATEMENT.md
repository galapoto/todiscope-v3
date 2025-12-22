# Architecture Closure Statement (v3)

v3 architecture is closed. The platform evolves by adding compliant engines and improving execution quality without changing core laws.

## Allowed in v3
- New engines that conform to the engine template contract and platform laws
- Performance improvements that preserve determinism and outputs
- Increased test coverage (detachability, determinism, enforcement)
- UX improvements that do not change platform semantics

## Requires a v4
- Weakening DatasetVersion enforcement or allowing implicit dataset selection
- Weakening evidence linkage requirements
- Introducing engine-to-engine runtime coupling
- Changing artifact storage semantics away from content-addressed payloads
- Introducing new platform execution abstractions (buses/brokers/microservices)

