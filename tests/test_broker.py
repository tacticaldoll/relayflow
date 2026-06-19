from relayflow.broker import InMemoryBroker, Job


def test_enqueue_and_reserve_carries_payload():
    b = InMemoryBroker()
    b.enqueue({"node_id": "a"})
    job = b.reserve()
    assert isinstance(job, Job)
    assert job.payload == {"node_id": "a"}
    assert b.reserve() is None


def test_unique_key_dedup_holds_one_job():
    b = InMemoryBroker()
    b.enqueue({"node_id": "a"}, unique_key="a")
    b.enqueue({"node_id": "a"}, unique_key="a")
    assert b.pending() == 1


def test_unique_key_freed_after_reserve_allows_reenqueue():
    b = InMemoryBroker()
    b.enqueue({"n": 1}, unique_key="k")
    b.reserve()
    b.enqueue({"n": 2}, unique_key="k")
    assert b.pending() == 1


def test_retry_redelivers_and_dead_letter_collects():
    b = InMemoryBroker()
    b.enqueue({"node_id": "a"}, unique_key="a")
    job = b.reserve()
    b.retry(job)
    assert b.pending() == 1
    job2 = b.reserve()
    b.dead_letter(job2)
    assert b.dead == [job2]
    assert b.pending() == 0
