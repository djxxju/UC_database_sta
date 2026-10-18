# Sources, licenses and attribution

The two originals in sources/or-lib/ are unchanged gzip files collected from the official UnitCommitment.jl 0.4 instance server on 2026-10-15. Both JSON payloads identify source-format version 0.3 and contain an explicit LICENSE granting MIT terms, copyright J E Beasley (2010). The complete notice is preserved in each payload and in [ORLIB_LICENSE.txt](sources/ORLIB_LICENSE.txt). This per-file evidence applies to these selected instances; it is not a blanket redistribution determination for every UC.jl external benchmark.

Official files:

- https://axavier.org/UnitCommitment.jl/0.4/instances/or-lib/10_0_4_w.json.gz
- https://axavier.org/UnitCommitment.jl/0.4/instances/or-lib/20_0_1_w.json.gz

Use the SHA-256 identities and original collection timestamps in pilot_manifest.json and per-case provenance.json; the external server URL is versioned but not guaranteed immutable. Source references embedded in each file:

- J. E. Beasley, OR-Library: distributing test problems by electronic mail, Journal of the Operational Research Society 41(11), 1990. DOI https://doi.org/10.2307/2582903 .
- A. Frangioni and C. Gentile, Solving nonlinear single-unit commitment problems with ramping constraints, Operations Research 54(4), 767–775, 2006. DOI https://doi.org/10.1287/opre.1060.0309 .

Also acknowledge the UnitCommitment.jl instance collection and original sources as requested by its documentation: https://github.com/ANL-CEEESA/UnitCommitment.jl , software DOI https://doi.org/10.5281/zenodo.4269874 . Source-reader semantics were reviewed at commit e4cc95dae16d9b8bccbfcd95ccf754b307d66c4a, not inferred from a newer default branch.

The derived files change cost interpolation and target model semantics. These changes and all assumptions are disclosed in provenance.json; no source optimum or feasibility claim is transferred. Original published data in https://github.com/djxxju/UC_datas_codex remain untouched.

The SJTU note is cited as an interface specification: https://notes.sjtu.edu.cn/s/zzB-Iq_eRD . This repository does not redistribute its full text or claim ownership of that specification. Third-party originals retain their own license; no new umbrella license is imposed here.
