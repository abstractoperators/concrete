# Benchmarks

## SWE Bench

SWE Bench in this module is copied over from the official [SWE Bench Github Page](https://github.com/princeton-nlp/SWE-bench)

Several components have been removed or modified to work with the concrete framework.

SWE Bench has a couple of components:
- Evaluation
- Dataset creation
  - Includes getters for GitHub issues
  - Includes RAG-like solutions for generating context for those issues
  - (Not implemented or documented for use with Concrete)
- Infererence

### Evaluation

Requires that you have a `.jsonl` predictions file with these columns.

```jsonl
{
    "instance_id": "<Unique task instance ID>",
    "model_patch": "<.patch file content string>",
    "model_name_or_path": "<Model name here (i.e. SWE-Llama-13b)>",
}
```

To run an evaluation on this file, run

```python
uv run python -m swebench.harness.run_evaluation \
    --dataset_name princeton-nlp/SWE-bench_Lite \
    --predictions_path <path_to_predictions> \
    --max_workers <num_workers> \
    --run_id <run_id>
```

Pre-curated datasets can be found on [Hugging Face](https://huggingface.co/princeton-nlp).
`predictions_path` refers to the path to the `.jsonl` file with the predictions.
`run_id` names the results for the run.

### Inference

You can either code your own application to create `jsonl` prediction files. Or you can use the `swebench.inference` module.

This module uses `swebench.inference` with a custom concrete method to generate predictions.

Run zero-shot predictions using an Operator

```python
uv run python -m swebench.inference.run_api \
  --dataset_name_or_path princeton-nlp/SWE-bench_oracle \
  --model_name_or_path concrete \
  --output_dir ./outputs
```

dataset_name_or_path refers to either a huggingface [dataset](https://huggingface.co/princeton-nlp), or a local path to a datset (local takes precedence). Dataset requires prompt `text` column that evaluation does not require. Precurated `_oracle` and `_bm25` datasets provide these, but you can also make them yourself.
model_name_or_path dictates what model is used for inference. Refer to `run_api.main` to see how this arg routes to inference methods.
output_dir is where the predictions will be saved. It will automaticall saved as `model__dataset__test.jsonl`



Lines Changed: +5, -2
Last Updated: 2024-12-06 16:23:00 UTC