"""usage rows and generation timings through PostgREST, as the app writes them."""
import random

from app.eta import Estimator, SupabaseTimings, features
from app.store.jobstore import SupabaseJobs
from app.usage import Meter, SupabaseUsage, set_scope

from .conftest import run, sql


def test_usage_rows_carry_user_job_and_cost(sb, user):
    job = run(SupabaseJobs(sb).create(user, "image", {}, 1))
    meter = Meter(SupabaseUsage(sb))

    async def go():
        set_scope(user_id=user, job_id=job.id)
        await meter.record("fal", "fal-ai/flux/schnell", "image", 2, "images", 0.006)
        set_scope(user_id=user, job_id="dev-not-a-uuid")
        await meter.record("openrouter", "m", "clean", 321, "tokens", 0.0012)

    run(go())
    rows = sql(f"select provider, units, unit, cost_usd, job_id is not null from public.usage where user_id = '{user}' order by id")
    assert rows.splitlines() == ["fal|2.00|images|0.006000|t", "openrouter|321.00|tokens|0.001200|f"]


def test_a_deleted_user_leaves_anonymous_usage_for_accounting(sb):
    import uuid

    uid = str(uuid.uuid4())
    sql(f"insert into auth.users (id, email) values ('{uid}', '{uid}@test.local')")

    async def go():
        set_scope(user_id=uid)
        await Meter(SupabaseUsage(sb)).record("fal", "m", "image", 1, "images", 0.01)

    run(go())
    sql(f"delete from auth.users where id = '{uid}'")
    assert sql("select count(*) from public.usage where user_id is null and model = 'm'") >= "1"


def test_learned_times_survive_a_restart(sb):
    sql("delete from public.generation_timings")
    rng = random.Random(7)

    def truth(x):
        return 3 + 2 * x[1] + 4 * x[2] + 1.5 * x[3]

    first = Estimator(SupabaseTimings(sb))
    for _ in range(40):
        x = features(rng.choice([1, 2, 4]), rng.choice([0, 1]), rng.randint(0, 5))
        run(first.observe("fal-ai/test", 10.0, x, truth(x), 1.0))
    assert sql("select count(*) from public.generation_timings") == "40"

    again = Estimator(SupabaseTimings(sb))  # a new process reads them back
    x = features(2, 1, 3)
    assert abs(run(again.estimate("fal-ai/test", 10.0, x)) - truth(x)) / truth(x) < 0.2
