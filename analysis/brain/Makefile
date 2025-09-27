ONTS = mba dmba hba dhba pba emapa

INPUT = results/brain.obo

# Assumption: Prepare.ipynb has been run to create the input obo files.

$(INPUT):
	robot merge $(patsubst %,-i results/source-%.obo,$(ONTS)) -o $@

# create sssom file from the obo files using lexmatch plus standard OBO weights
results/lexmatch.sssom.tsv: $(INPUT)
	runoak -i simpleobo:$< lexmatch  -R config/lexmatch-config.yaml -o $@
.PRECIOUS: results/lexmatch.sssom.tsv

# create ptable from the sssom file using sssom-py
# NOTE: a limitation of this approach is that we don't include the non-probabilistic
# facts from the obo files.
results/lexmatch.ptable.tsv: results/lexmatch.sssom.tsv
	boomerang ptable $< > $@
.PRECIOUS: results/lexmatch.ptable.tsv

results/kb-full.yaml:
	uv run boomer-cli merge results/kb.yaml results/lexmatch.ptable.tsv -o $@

#results/boomer.yaml: results/lexmatch.ptable.tsv
results/boomer.yaml: results/kb-full.yaml
	uv run boomer-cli solve -t 10 --max-solutions 300 --max-pfacts-per-clique 100 -f yaml $< -o $@ -O yaml -d results/boomer

results/grid.json: results/kb-full.yaml
	uv run boomer-cli grid-search  $< config/brain-grid.yaml -e results/target_kb.yaml -o $@  -d results/grid


