def compile_static_context_packet(
  manifest_path: Path,
  harness_root: Path,
  target_repo_root: Path,
  output_path: Path,
) -> StaticContextPacket:
  manifest = load_and_validate_manifest(manifest_path)

  included = {}
  source_coverage = []
  missing_sources = []
  invalid_sources = []

  for source in manifest.sources:
    paths = resolve_source_paths(source, harness_root, target_repo_root)

    # cardinality + requiredness checks
    # json load
    # schema validation
    # included[source.source_id] = loaded_json

  packet = StaticContextPacket(
    metadata=StaticContextPacketMetadata(
      document_id="static_context_packet.json",
      title="Static Context Packet",
      purpose="Compiled static authority and operational context from StaticContextPacketManifest.",
      source_format="json",
      document_authority="generated_artifact",
    ),
    governance_primitives=included["governance_primitives"],
    project_spec=included["project_spec"],
    known_failures=included["known_failures"],
    open_decisions=included["open_decisions"],
    active_implementation_plan=included.get("active_implementation_plan"),
    active_implementation_tracker=included.get("active_implementation_tracker"),
    source_coverage=source_coverage,
    missing_sources=missing_sources,
    invalid_sources=invalid_sources,
  )

  write_json(output_path, packet.model_dump(mode="json"))
  return packet