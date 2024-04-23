import toml
import subprocess
import os
import json
import time
import pyarrow as pa
import pyarrow.parquet as pq
import datetime


def run_command(command, cwd) -> float | None:
    try:
        start_time = time.time()
        subprocess.run(command, cwd=cwd, shell=True, check=True)
        elapsed_time = time.time() - start_time
        return elapsed_time
    except subprocess.CalledProcessError as e:
        print(f"An error occurred while executing: {command}")
        print(f"Error: {e}")
        return None


def build_reader(cwd, reader):
    build_steps = reader["build"]
    for step in build_steps:
        # Execute each command in the shell
        ok = run_command(step, cwd)
        if not ok:
            break


def benchmark_one(reader, workload) -> dict | None:
    workspace_dir = os.path.dirname(os.path.realpath(__file__))
    working_dir = os.path.join(workspace_dir, reader["working_dir"])

    executable_path = os.path.join(working_dir, reader["bin"])
    workload_path = os.path.join(workspace_dir, workload["path"])

    elapsed = run_command(f"{executable_path} {workload_path}", working_dir)
    if not elapsed:
        return None

    print(
        f"Reader: {reader['name']}, File: {workload['path']}, Elapsed time: {elapsed}s"
    )

    return {
        "reader": reader,
        "workload": workload,
        "result": {
            "elapsed": elapsed,
        },
    }


def benchmark(readers, workloads):
    workspace_dir = os.path.dirname(os.path.realpath(__file__))
    results = []

    for r in readers:
        working_dir = os.path.join(workspace_dir, r["working_dir"])
        build_reader(working_dir, r)
        for f in workloads:
            r = benchmark_one(r, f)
            results.append(r)
    return results


def save_results(results, dst_dir):
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    time_str = now.strftime("%H-%M")

    date_directory = os.path.join(dst_dir, date_str)

    if not os.path.exists(date_directory):
        os.makedirs(date_directory)

    json_file = os.path.join(date_directory, f"{time_str}-results.json")
    try:
        with open(json_file, "w") as f:
            json.dump(results, f, indent=4)
            print(f"Json results saved to {json_file}")
    except Exception as e:
        print(f"Failed to save the json file: {e}")

    try:
        parquet_file = os.path.join(date_directory, f"{time_str}-results.parquet")
        table = pa.Table.from_pylist(results)
        pq.write_table(table, parquet_file)
        print(f"Parquet results saved to {parquet_file}")
    except Exception as e:
        print(f"Failed to save the parquet file: {e}")


if __name__ == "__main__":
    with open("config.toml") as f:
        config = toml.load(f)

    workspace_dir = os.path.dirname(os.path.realpath(__file__))

    output_dir = os.path.join(workspace_dir, "results")
    results = benchmark(readers=config["readers"], workloads=config["workloads"])
    save_results(results, output_dir)
