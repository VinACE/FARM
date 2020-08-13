"""
This benchmarks the time taken by preprocessing / language modelling / prediction head processing.
This is done by running the Inferencer twice: once with ph enabled and once with ph disabled.
The Inferencer contains a Benchmarker object which measures the time taken by preprocessing and model processing.
"""

from farm.infer import Inferencer
from pprint import pprint
import pandas as pd
from tqdm import tqdm


task_type = "question_answering"
sample_file = "samples/question_answering_sample.txt"
questions_file = "samples/question_answering_questions.txt"
num_processes = 1

params = {
    "modelname": ["deepset/bert-base-cased-squad2", "deepset/minilm-uncased-squad2", "deepset/roberta-base-squad2", "deepset/bert-large-uncased-whole-word-masking-squad2", "deepset/xlm-roberta-large-squad2"],
    "batch_size": [16, 32, 64],
    "document_size": [10_000, 100_000, 1000_000],
    "max_seq_len": [384, 512, 1024],
    "doc_stride": [128],
    "gpu": [True],
    "question": [l[:-1] for l in open(questions_file)][:2]
}

def benchmark(params, output="results_component_test.csv"):
    ds = generate_param_dicts(params)
    print(f"Running {len(ds)} benchmarks...")
    results = []
    for d in tqdm(ds):
        result = benchmark_single(**d)
        results.append(result)
    for result in results:
        pprint(result)
        print()
    df = pd.DataFrame.from_records(results)
    df.to_csv(output)


def benchmark_single(batch_size, gpu, max_seq_len, doc_stride, document_size, question, modelname):
    try:
        input_dict = prepare_dict(sample_file, question, document_size)

        # Run once with dummy prediction heads
        inferencer_dummy_ph = Inferencer.load(modelname,
                                              batch_size=batch_size,
                                              gpu=gpu,
                                              task_type=task_type,
                                              max_seq_len=max_seq_len,
                                              num_processes=num_processes,
                                              doc_stride=doc_stride,
                                              dummy_ph=True,
                                              benchmarking=True)
        inferencer_dummy_ph.inference_from_dicts(input_dict)
        preproc_lm_only, model_lm_only = inferencer_dummy_ph.benchmarker.summary()

        # Run once with real prediction heads
        inferencer_real_ph = Inferencer.load(modelname,
                                             batch_size=batch_size,
                                             gpu=gpu,
                                             task_type=task_type,
                                             max_seq_len=max_seq_len,
                                             num_processes=num_processes,
                                             doc_stride=doc_stride,
                                             dummy_ph=False,
                                             benchmarking=True)
        inferencer_real_ph.inference_from_dicts(input_dict)
        preproc_full, model_full = inferencer_real_ph.benchmarker.summary()

        ave_preproc, lm_time, ph_time, total = analyse_timing(preproc_lm_only, model_lm_only, preproc_full, model_full)
        result = {"model name": modelname,
                  "question": question,
                  "preproc": ave_preproc,
                  "language model": lm_time,
                  "prediction head": ph_time,
                  "total": total,
                  "batch_size": batch_size,
                  "document_size": document_size,
                  "num_processes": num_processes,
                  "max_seq_len": max_seq_len,
                  "doc_stride": doc_stride,
                  "gpu": gpu,
                  "sample_file": sample_file,
                  "error": ""
                  }
    except Exception as e:
        result = {"model name": modelname,
                  "question": question,
                  "preproc": -1,
                  "language model": -1,
                  "prediction head": -1,
                  "total": -1,
                  "batch_size": batch_size,
                  "document_size": document_size,
                  "num_processes": num_processes,
                  "max_seq_len": max_seq_len,
                  "doc_stride": doc_stride,
                  "gpu": gpu,
                  "sample_file": sample_file,
                  "error": str(e)
                  }
    return result


def generate_param_dicts(params):
    state = {}
    result = []
    params = {k: list(v) for k, v in params.items()}
    param_names = list(params)
    recurse(param_names, state, result)
    return result

def recurse(param_names, state, result):
    if len(param_names) == 0:
        result.append(dict(state))
        return

    curr_pn = param_names[0]
    param_names = param_names[1:]
    for x in params[curr_pn]:
        state[curr_pn] = x
        recurse(param_names, state, result)


def prepare_dict(sample_file, q, document_size):
    with open(sample_file) as f:
        text = f.read()[:document_size]
        assert len(text) == document_size
    dicts = [{"qas": [q], "context": text}]
    return dicts


def analyse_timing(preproc_lm_only, model_lm_only, preproc_full, model_full):
    ave_preproc = (preproc_lm_only + preproc_full) / 2
    lm_time = preproc_lm_only + model_lm_only

    init_to_formatted_lm = preproc_lm_only + model_lm_only
    init_to_formatted_full = preproc_full + model_full
    ph_time = init_to_formatted_full - init_to_formatted_lm

    total = init_to_formatted_full
    return ave_preproc, lm_time, ph_time, total

if __name__ == "__main__":

    benchmark(params)
