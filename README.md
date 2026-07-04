# py_ez_wikidata
Mapping for Wikidata allows simplified / easy creation of wikidata entries from dicts

[![Join the discussion at https://github.com/WolfgangFahl/py_ez_wikidata/discussions](https://img.shields.io/github/discussions/WolfgangFahl/py_ez_wikidata)](https://github.com/WolfgangFahl/py_ez_wikidata/discussions)
[![pypi](https://img.shields.io/pypi/pyversions/py_ez_wikidata)](https://pypi.org/project/py_ez_wikidata/)
[![Github Actions Build](https://github.com/WolfgangFahl/py_ez_wikidata/actions/workflows/build.yml/badge.svg)](https://github.com/WolfgangFahl/py_ez_wikidata/actions/workflows/build.yml)
[![PyPI Status](https://img.shields.io/pypi/v/py_ez_wikidata.svg)](https://pypi.python.org/pypi/py_ez_wikidata/)
[![GitHub issues](https://img.shields.io/github/issues/WolfgangFahl/py_ez_wikidata.svg)](https://github.com/WolfgangFahl/py_ez_wikidata/issues)
[![GitHub closed issues](https://img.shields.io/github/issues-closed/WolfgangFahl/py_ez_wikidata.svg)](https://github.com/WolfgangFahl/py_ez_wikidata/issues/?q=is%3Aissue+is%3Aclosed)
[![API Docs](https://img.shields.io/badge/API-Documentation-blue)](https://WolfgangFahl.github.io/py_ez_wikidata/)
[![License](https://img.shields.io/github/license/WolfgangFahl/py_ez_wikidata.svg)](https://www.apache.org/licenses/LICENSE-2.0)

## Docs
[Wiki](https://wiki.bitplan.com/index.php/Py_ez_wikidata)

## CLI (ezwd)
`ezwd` creates Wikidata items from a simple YAML/JSON record via a named property
mapping. It is **dry-run by default** — add `-w` to actually write.

### Search
```bash
ezwd -s "Robert David"
```

### Inspect a mapping
```bash
ezwd -m scholar --list-mappings
```

### Create from a record
`robert_david.yaml`:
```yaml
label: Robert David
description: knowledge graph researcher
instanceof: Q5
orcid: "0000-0002-3244-5341"
dblp: "173/3493-1"
linkedInId: "robert-david-39b47692"
```
```bash
# dry-run (nothing written)
ezwd -m scholar -r robert_david.yaml
# write to production Wikidata
ezwd -m scholar -r robert_david.yaml -w
```
The example above created [Q140424194](https://www.wikidata.org/wiki/Q140424194)
(instance of human, with ORCID, DBLP and LinkedIn). Only add an identifier once
you have verified it belongs to this exact person — do not bulk-copy IDs from an
author record that may aggregate homonyms.

### Endpoint selection
```bash
ezwd -m scholar -r robert_david.yaml --test    # target test.wikidata.org
ezwd -m scholar -r robert_david.yaml --baseurl https://www.wikidata.org
```
Note: `test.wikidata.org` uses different property / item IDs than production, so a
production-PID mapping (like `scholar`) will not validate there without a
test-specific mapping.
