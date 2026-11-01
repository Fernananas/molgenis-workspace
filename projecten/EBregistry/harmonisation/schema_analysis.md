# EB Registry: Source-to-Target Schema Analysis (Phase 1)

Basis: `source_schema.csv`, `target_schema.csv`, `target_ontology/*.csv` only. No patient data was used.
Machine-checked by `tools/validate_config.py` (0 errors; 5 warnings = required target fields with no source, see section 4).

## 1. Shape of the two schemas

| | Source | Target |
|---|---|---|
| Tables | 1 flat table `EBpatients`, 130 columns (Dutch labels, ISO-8859-1) | 3 data tables `Individuals`, `Biopsies`, `Variants` + 20 ontology tables |
| Typing | None. Only 11 columns typed `text`, the rest blank. No refs, no descriptions, no value lists | Typed: ontology, ontology_array, bool, date, int, text, ref, refback, auto_id |
| Key | `patientCode` (key, required) | `patientCode` (auto_id), `biopsyId`, `variantId` |

Target field kinds
- **Ontology (38 + 1 array):** sex, ethnicity, country, EB type/subtypes, inheritance, diagnosis method, patient status, material, gene, transcript, biopsy type/location, blister level, 16 protein-expression fields, filament/hemidesmosome/anchoring-fibril/lamina-densa status.
- **Bool (7), date (5), int (3), text (7), ref (2).** `refback` (`biopsy`, `genes`) and `heading` rows hold no data.

## 2. Proposed table-level mapping

| Source | Target | Cardinality |
|---|---|---|
| `EBpatients` (demographics, status, diagnosis, derived flags) | `Individuals` | 1 : 1 |
| `EBpatients` (`if*` columns) | `Biopsies` (kindOfEntry = Immunofluorescence) | 1 : 0..1 |
| `EBpatients` (`em*` columns) | `Biopsies` (kindOfEntry = Electron microscopy) | 1 : 0..1 |
| `EBpatients` (`gen`, `allel1/2`) | `Variants` | 1 : 0..1 |

Source `patientCode` is reused as the link key; the pipeline generates `Individuals.patientCode` through a local crosswalk.

## 3. Column mappings (summary)

Confidence: H = label and type agree, M = plausible, L = guess. Full detail and notes are in `config/*.yaml`; per-source-column status is in `docs/mapping_matrix.csv`.

| Target | Source | Transform | Conf. |
|---|---|---|---|
| Individuals.patientCode | patientCode | link_key (generated) | M |
| internalPatientCode | patientCode | copy | M |
| dateOfInitialClinicalAssessment | eersteBezoekdatum | parse_date | M |
| treatmentCountry / treatmentCenter | none (constants Netherlands / UMCG) | constant | M |
| dateOfBirth | gebDat | parse_date | H |
| biologicalSexAtBirth | geslacht | lookup | M |
| ethnicity | none (constant "Not recorded") | constant | M |
| majorEbType | diagnoseCode, fallback `gen` | coalesce + lookup | L |
| howWasDiagnosisMade | ifNummer, emNummer, gen | rules | M |
| diseaseInheritance | erf | lookup | M |
| *-InvestigationBool, *NumberOfBiopsies, geneticTesting, numberOfAffectedGenes | if*/em*/dnaOnderzoekIngezet/gen | any_present / count_present | M/L |
| patientStatus | overleden + datumOverlijden | rules | M |
| dateOfDeath | datumOverlijden | parse_date | H |
| Biopsies (IF) 16 protein fields | ifEiwit1-4 + ifAankleuring1-4, ifKeratin14, ifBp180_1d1, ifNiceineGb3, ifCollageenViiLh7_2 | paired_lookup / coalesce | L-M |
| Biopsies.proteinsStained | derived from the protein fields | list_from_target | M |
| Biopsies (EM) | emBioptLokaties, emAnchoringFibrils, emHemidesmosomen, emTonofilamenten | lookup | L-M |
| Variants.affectedGene / referenceSequence | gen | lookup (gene to transcript) | M |
| Variants.cdnaofThisAffectedGene / cdnaOfAllele2 | allel1 / allel2 | copy | L |
| Variants.isTheSecondAlleleForThisGeneDifferent | allel1, allel2 | differs | L |

### Source fields split across several targets
- `patientCode` feeds Individuals.patientCode, internalPatientCode and the FK in Biopsies/Variants.
- `gebDat` feeds dateOfBirth (and age, if enabled).
- `datumOverlijden` feeds dateOfDeath and patientStatus.
- `gen` feeds affectedGene, referenceSequence, detailsOfOther*, numberOfAffectedGenes, geneticTesting and (fallback) majorEbType.
- `diagnoseCode` feeds majorEbType and, once rules exist, the EBS/JEB/DEB subtype.
- `ifNummer` / `emNummer` feed the investigation booleans, biopsy counts, howWasDiagnosisMade and biopsy-row creation.

### Several source fields feeding one target
- `proteinsStained` and each protein field: free-text name (`ifEiwit1-4`) + paired result (`ifAankleuring1-4`) + fixed antibody columns.
- `howWasDiagnosisMade`: ifNummer, emNummer, gen. `patientStatus`: overleden + datumOverlijden.
- `isTheSecondAlleleForThisGeneDifferent`: allel1 + allel2.
- Biopsies.otherInformation could take the IF/EM report and remark fields (disabled for privacy).

## 4. Target fields with no usable source

Required (load will fail validation until resolved):
- `Individuals.patientCountryOfOrigin`: no source; residence is not origin.
- `Individuals.dateOfDiagnosis`: only first-visit date exists.
- `Individuals.thisDiagnosisRequiresSupportOrConfirmationFromDCC`, `diagnosisConfirmedByDiagnosticCurationCommittee`: registry-side concepts.
- `Individuals.age`: disabled, see 6.1.

Optional: antibody clones (12 fields), levelOfBlistering, laminaDensa, detailsOfOther*, subtype fields (need clinical rules), whatMaterialStored.

## 5. Source fields with no clear destination

Complete list with reasons: `unmapped:` in `config/pipeline.yaml` (130 of 130 columns accounted for).

- **Direct identifiers, deliberately not migrated (13):** names, umcgNr, bsn, address, phone, email, `brief`, `dossiernummerKg`.
- **Clinical phenotype (35):** skin, mouth, nail, GI/GU, hand/foot, anaemia, growth. The target has none; candidate schema extension.
- **Follow-up/referral:** datumLaatsteBezoek, leeftijdBijLaatsteBezoek, verwijzer, plaatsVerwijzer, famAnamnese, redenVanOverlijden.
- **Light microscopy:** lmNummer, lmVerslag (no LM biopsy type).
- **Variant detail:** protein level, exon, mutation type, origin, parental genotype, polymorphisms, revertant, genotype.
- **Ambiguous (label alone is not enough):**
  - `dna`, `dnaBij`: DNA stored vs tested vs where?
  - `gen1-4` + `afgerond1-4`: genes ordered/tested (with "completed"), or affected genes?
  - `mutatie`, `mutatieGevonden`: combined mutation string? Found yes/no?
  - `emAfs` vs `emAnchoringFibrils`: duplicate?
  - `emSbdp`: sub-basal dense plate? Not lamina densa.
  - `ifCol7Lh7_2CoPlus`: duplicate COL7 or co-staining?
  - `leeftijd`: age at export (stale).
  - `selecteer`: probably a UI flag.
  - `retentieBasaleCellen`.

## 6. Pitfalls found (do not trust name similarity)

1. **`age` is typed `date` and required** in the target; likely a schema error. Left disabled.
2. **`ifNiceineGb3` is nicein = laminin-332, not kindlin-1.** Mapped to `laminin332`.
3. **Typos matter for exact matching:** ontology term `Immunoflurescence`; field `immunofluorescencenceDiagnosticInvestigation`.
4. **Ontology `name` vs `label`:** names are numeric codes (`0,1,2,9`). The YAML uses labels; `ontology_output` switches it. Confirm what EMX2 import expects.
5. **Ontology gaps:** BiologicalSex and PatientStatus lack "unknown"; AnchoringFibrils lacks "Hypoplastic" (caught by the validator). Blank source values must stay empty, not be forced to a term.
6. **Single-value targets for multi-value reality:** whatMaterialStored, locationOfBiopsy, otherProteins hold one value.
7. **`geslacht` may be current gender, not sex at birth.**
8. **Count fields cannot be reconstructed:** one `ifNummer`/`emNummer` column means counts are 0/1 at best.
9. **Auto-id key:** confirm the importer accepts supplied `patientCode`/FK values.
10. **Privacy:** free-text reports (`*Verslag`, `*Opmerkingen`) are mapped only in disabled `otherInformation` mappings; dateOfBirth is a full date; the key crosswalk is confidential.

## 7. Running the checks

    python tools/validate_config.py --schemas <path-to>/schemas

Next phases (not built yet): `profile` command (value frequencies with small-count suppression, free text and identifiers skipped) to replace guessed `values:`; engine implementing the transform vocabulary in `config/pipeline.yaml`; synthetic-data tests.
