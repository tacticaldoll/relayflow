import pytest

from relayflow.artifact import ArtifactStore
from relayflow.demo import demo_execution
from relayflow.executor import (
    ExecResult,
    ExecSpec,
    FileScopeViolation,
    MockExecutor,
    in_scope,
    run_execution,
)


def spec(allowed=None):
    return ExecSpec(
        id="job",
        scope="exec",
        instruction="do a thing",
        allowed_paths=allowed if allowed is not None else ["src/"],
    )


def result(files, status="passed"):
    return ExecResult(
        patch="--- a/x\n+++ b/x\n+change\n",
        summary="did a thing",
        tests="ok",
        status=status,
        files=files,
    )


# --- interface -------------------------------------------------------------


def test_mock_executor_returns_full_result():
    r = MockExecutor(result=result(["src/a.py"])).run(spec())
    assert r.patch and r.summary and r.tests
    assert r.status == "passed"
    assert r.files == ["src/a.py"]


# --- patch & test artifacts ------------------------------------------------


def test_execution_writes_resolvable_patch_and_test_artifacts():
    store = ArtifactStore()
    executor = MockExecutor(result=result(["src/a.py"], status="passed"))
    patch_ref, test_ref = run_execution(store, executor, spec())

    patch = store.resolve(patch_ref)
    assert patch.type == "patch"
    assert patch.metadata["summary"] == "did a thing"
    assert patch.metadata["files"] == ["src/a.py"]

    test = store.resolve(test_ref)
    assert test.type == "test"
    assert test.metadata["status"] == "passed"


# --- file scope guard ------------------------------------------------------


def test_in_scope_prefix_containment():
    assert in_scope("src/a.py", ["src/"])
    assert in_scope("src", ["src"])
    assert not in_scope("secrets.txt", ["src/"])
    assert not in_scope("srcx/a.py", ["src/"])


def test_in_scope_patch_writes_artifacts():
    store = ArtifactStore()
    executor = MockExecutor(result=result(["src/a.py", "src/sub/b.py"]))
    patch_ref, test_ref = run_execution(store, executor, spec(["src/"]))
    assert store.resolve(patch_ref).type == "patch"
    assert store.resolve(test_ref).type == "test"


def test_out_of_scope_patch_rejected_and_nothing_written():
    store = ArtifactStore()
    executor = MockExecutor(result=result(["src/a.py", "secrets.txt"]))
    with pytest.raises(FileScopeViolation):
        run_execution(store, executor, spec(["src/"]))
    # nothing was written
    assert store.latest("exec") == []


# --- demo ------------------------------------------------------------------


def test_demo_execution_runs_in_scope():
    store = ArtifactStore()
    executor, demo_spec = demo_execution()
    patch_ref, test_ref = run_execution(store, executor, demo_spec)
    assert store.resolve(patch_ref).type == "patch"
    assert store.resolve(test_ref).metadata["status"] == "passed"
