---
title: EUSTIA Canonical Migration Integrity Audit
status: verified_pending_remote_readback
agent_id: CODEX
branch: codex/migration/final-canonical-cutover
source_root: D:/LiblibAI-workspace/comfyui-deploy-win/ComfyUI/output
audit_date: 2026-08-12
---

# EUSTIA Canonical Migration Integrity Audit

## 1. Source evidence and destination data

The supplied D: source files were present and matched the preserved local migration inputs byte-for-byte before writing. `ReadAllLines(UTF-8)` is the line-count method used here. The user-provided earlier counts (1265 / 358 / 142) do not match the currently supplied byte-identified files; this audit therefore reports the reproducible current file counts below rather than asserting the older figures.

| Canonical | Source bytes | Source lines | Source SHA-256 | Destination bytes | Destination lines | Destination SHA-256 |
|---|---:|---:|---|---:|---:|---|
| AI电影系统.md | 38855 | 1767 | E8817BB10969AB64C3668D500DB430CC27B61FB21EADEF8C27FAABD4379B767E | 39009 | 1670 | D11BC915E153CFC86006F105E34CC40E3D8E6D80A7CB512E66326073493A5B34 |
| AI电影项目记忆.md | 18051 | 490 | 9BA184D7D5EC122E6FA9E0CD650D6133E1E87591324FEC2D4A3283B5DE1F6744 | 18723 | 494 | 70DAC33A853EC992FDA894C8116F92FD56EB1AD4852FB516629F75D5C4838E2A |
| 场景与空间设定库.md | 3791 | 172 | 43F504772B51530B2D7B7675A3675552C5611611100D68E7BE4FA564A99D03FF | 4732 | 174 | 3A62AEF3114027ED65DC71098A1747AAAE4CF1D8750570B53DEA7DB52EC219CC |

## 2. Migration method

Each fixed destination was restored from the supplied complete source, not reconstructed from memory, older chats, a former total outline, or the prior compressed GitHub document. Source text was retained chapter-for-chapter. The AI电影系统 editor normalized blank-line formatting while applying the complete source; this is a formatting-only source/destination difference. No substantive source paragraph was deleted to make the document shorter.

## 3. Exact reconcile list

### AI电影系统.md

| Source location | Change | Reason / authority |
|---|---|---|
| Header and 0.1 | Added GitHub-first runtime note; replaced `../02_外部记忆系统/外部记忆系统.md` with PROJECT_INDEX-led reads of project memory, screenplay, map, and existing canonical libraries | `PROJECT_INDEX.yaml`, `read_sets.yaml`, `write_routes.yaml`, and `source_authority.yaml` are current authority; old external-memory path has no active repository target |
| 0.1A | Replaced external-memory read/write links with project memory, feedback engine, and unique write routes | Memory is auxiliary only; current GitHub canonical must prevail |
| 10 | Replaced generic “external memory” write target with explicit current write routes | Avoids reviving an obsolete authority path without removing learning schema or workflow |
| 11 | Added `DIRECTOR-FULL-OUTPUT-001` identifier to the unchanged fifteen-item default output contract | Preserves and regression-tests the existing full director contract |
| 18 | Added PROJECT_INDEX/read_sets pre-read before the unchanged automatic execution list | Ensures runtime invokes the migrated canonical through current source authority |
| historical change log | Marked old external-memory reading/writing statements as historical and superseded by current routes | History remains visible but cannot be read as active authority |
| section 15 | Added CALC/CLCS, timecode, and six-degrees runtime terminology mapping to existing full-source rules | Required by existing GitHub runtime regressions; does not remove or replace original rules |

### AI电影项目记忆.md

| Source location | Change | Reason / authority |
|---|---|---|
| Header, 0.4, 17A, 19 | Replaced active long-term-memory file links with PROJECT_INDEX-first GitHub canonical routing; external Memory remains explicitly auxiliary | No active in-repository long-term-memory file exists; `PROJECT_INDEX.yaml` is source registry |
| 9.1 / 9.5 | Reconciled “high tower / upper route” wording to church bell tower → checkpoint rear ground entrance → checkpoint internal spiral stair | `05_场景与空间/00_项目地图文件.md` is topology SSOT and explicitly resolves the conflict |
| 17A.2 | AIP-001 retained verbatim in substance: Seedance naturally allocates duration unless beat/sync/point editing needs timecode | High-confidence supplied project rule retained |

### 场景与空间设定库.md

| Source location | Change | Reason / authority |
|---|---|---|
| Header and section 2 | Changed topology claims to a local historical/prompt context and explicitly named the canonical map as topology SSOT | The map owns direction, adjacency, height, entrances, and reachable routes |
| section 4 | Replaced “external memory chapter 8” with the GitHub project-memory reference | Old external path is not an active canonical |
| sections 8–9 | Separated church bell tower from checkpoint; revised upper passage as checkpoint-internal controlled route | Matches map’s locked bell-tower/checkpoint ruling; preserves institutional, material, light, prop, and prompt content |

## 4. Deleted, moved, duplicate, and unresolved content

- Deleted substantive source content: none.
- Deleted formatting: only Markdown trailing spaces and editor-normalized blank lines; no rule, list item, chapter, source citation, or production instruction was deleted for compression.
- Moved substantive source content: none. Existing facts retain their source sections; runtime ownership is clarified by references, not copy-removal.
- Duplicate replacement: old external-memory paths were replaced only where they named an unavailable active authority. Their historical evolution records remain in place.
- Unresolved content: `U-ASSET-RETRIEVAL-001` remains open in `UNKNOWN_REGISTRY.yaml`; it concerns formal image-pixel retrieval and does not block text canonical migration.

## 5. Authority and dry-run acceptance criteria

The three destination paths remain the fixed canonical paths in `PROJECT_INDEX.yaml`. Their effective sources may be reported as `github_verified` only after the tested branch is committed, pushed, and the identical remote head is read back.

Dry run task: “对凯姆、菲奥奈、市集/钟楼附近的一段剧情进行导演分析。” Required route:

```text
PROJECT_INDEX.yaml
→ read_sets.yaml (directing)
→ director_route_index.yaml (space / continuity symptoms)
→ AI电影系统 relevant sections only
→ 当前改编剧本 hit range
→ 角色与表演设定库 (凯姆、菲奥奈)
→ 场景与空间设定库 (市集 / 钟楼 local properties)
→ 00_项目地图文件 (mandatory spatial authority)
→ 连续性与当前生产状态
→ 视觉资产登记 (only bound assets needed)
→ 反馈反推与系统反哺引擎
```

The dry run must demonstrate local targeted retrieval, map-forced spatial reads, GitHub canonical precedence, no Memory override, rejection of legacy total outlines, and invocation of all three migrated canonicals.
