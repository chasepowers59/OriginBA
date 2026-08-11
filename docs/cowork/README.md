# OriginBA Claude Co-work Bundle

Use this folder to configure Claude Co-work for Oracle C2M + Jaspersoft Server 9.x work in this repository.

## Setup

1. Paste `system_directions.md` into Co-work custom instructions.
2. Add the six skills from `skills/` as Co-work skills (one file per skill).
3. Pin the files listed in `memory_manifest.md` into Co-work project memory.
4. Use `starter_prompt.md` at the beginning of each session.

## Files

| File | Purpose |
|------|---------|
| `system_directions.md` | Master system prompt / custom instructions |
| `memory_manifest.md` | Tiered list of repo paths to attach to memory |
| `starter_prompt.md` | Copy-paste session opener |
| `skills/*.md` | Six task-specific Co-work skills |

## Related repo paths

The skills reference canonical sources under:

- `AGENTS.md`
- `docs/c2m_jaspersoft_delivery_playbook.md`
- `docs/assistant_skills/`
- `skills/` (Cursor/project skills)
- `knowledge_base/`
- `output/ai_cisadm_context.json`
- `output/domain_field_index.json`
- `output/workstream_reporting_dictionary.json`

Do not add `.env`, ZIP archives, or large log folders to Co-work memory.
