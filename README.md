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
* [Tutorial](https://wiki.bitplan.com/index.php/Py_ez_wikidata/Tutorial) - mapping, record, dry run, author order and the worked examples
* [Wiki](https://wiki.bitplan.com/index.php/Py_ez_wikidata) - project page and release notes

## Install
```bash
pip install py-ez-wikidata
```

## CLI (ezwd)
`ezwd` creates a Wikidata item from a YAML/JSON record via a named property
mapping. It is **dry-run by default** — add `-w` to actually write.
```bash
ezwd -m scholar --list-mappings            # the columns of a mapping
ezwd -m scholar --example                  # the worked example embedded in the mapping
ezwd -m scholar -r robert_david.yaml --strict   # your record as dry-run, exit 1 on problems
```
`robert_david.yaml`:
```yaml
label: Robert David
description: knowledge graph researcher
instanceof: Q5
orcid: "0000-0002-3244-5341"
dblp: "173/3493-1"
linkedInId: "robert-david-39b47692"
```
This record created [Q140424194](https://www.wikidata.org/wiki/Q140424194).
Only add an identifier once you have verified it belongs to this exact person.

`--format turtle` prints the built item as RDF in the Wikidata model,
`-s "Robert David"` searches Wikidata before you create, `--test` targets
test.wikidata.org.

## Bundled mappings
| name | creates | example |
|---|---|---|
| `scholar` | human ([Q5](https://www.wikidata.org/wiki/Q5)) with scholarly identifiers | [Q140424194](https://www.wikidata.org/wiki/Q140424194) |
| `paper` | scholarly article ([Q13442814](https://www.wikidata.org/wiki/Q13442814)), authors in their order | [Q141609355](https://www.wikidata.org/wiki/Q141609355) |
| `proceedings` | CEUR-WS proceedings volume ([Q1143604](https://www.wikidata.org/wiki/Q1143604)) | [Q141623730](https://www.wikidata.org/wiki/Q141623730) |
| `event` | event of a CEUR-WS volume, class from the record | [Q141623731](https://www.wikidata.org/wiki/Q141623731) |
| `extension` | MediaWiki extension ([Q6805426](https://www.wikidata.org/wiki/Q6805426)) | [Q140770649](https://www.wikidata.org/wiki/Q140770649) |

Every mapping file carries the record of its example in its header, how this
works and all five examples are in the
[tutorial](https://wiki.bitplan.com/index.php/Py_ez_wikidata/Tutorial/Examples).
