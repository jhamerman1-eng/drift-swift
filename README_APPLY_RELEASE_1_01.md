# How to apply Release 1.01 patch and tag

1) Copy these three files into your **repo root**:
   - `release_1_01.patch`
   - `tag_release_1_01.sh` (macOS/Linux) **or** `tag_release_1_01.ps1` (Windows PowerShell)

2) (Optional) Preview what will change:
```bash
git apply --check release_1_01.patch
```

3) Apply + commit + tag + push (macOS/Linux):
```bash
chmod +x ./tag_release_1_01.sh
./tag_release_1_01.sh main
```

   Windows PowerShell:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.	ag_release_1_01.ps1 -Branch main -PatchFile .elease_1_01.patch
```

If you see “No changes to commit”, it means your repo already contains identical content.

## Notes
- Patch **adds**/updates files under:
  `configs/`, `libs/runtime/`, `libs/drift/drivers/`, `bots/`, `orchestrator/`, `tests/`, `.env.example`, `requirements.txt`, `README.md`, `RELEASE_NOTES_v1.01.md`, `VERSION`.
- Tag created: **v1.01**
- To remove the tag locally and remotely:
```bash
git tag -d v1.01
git push origin :refs/tags/v1.01
```
