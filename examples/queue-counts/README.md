# Count jobs in Mission Control and Solid Queue

In `mission_control-jobs` 1.3.1, the Solid Queue adapter cannot count or enumerate the status-less `ActiveJob.jobs` relation. The README's “All jobs” example is misleading for this adapter: constructing that relation succeeds, but evaluating its count reaches `execution_class_by_status` without a status and raises `ActiveJob::Errors::QueryError`.

Adding `where` alone does not select a status. Choose a status for the Mission Control API, or use Solid Queue's ActiveRecord model when you mean all retained database rows.

## Use an explicit status

Run these in your application's Rails console, with Mission Control and the Solid Queue adapter already configured:

```ruby
ActiveJob.jobs.failed.count
ActiveJob.jobs.pending.where(queue_name: "default").count
ActiveJob.jobs.failed.where(job_class_name: "SomeJob").count

# Listing uses the same status requirement.
ActiveJob.jobs.failed.where(queue_name: "default").limit(10).to_a
```

The names differ between the two libraries:

| Mission Control scope | Solid Queue state | Meaning |
| --- | --- | --- |
| `pending` | ready | Queued and ready to be claimed |
| `scheduled` | scheduled | Waiting for its scheduled time |
| `blocked` | blocked | Waiting for a concurrency slot |
| `in_progress` | claimed | Claimed by a worker |
| `failed` | failed | Failed execution retained for inspection/retry |
| `finished` | finished | Completed job row still retained |

`pending` is **not** every unfinished job. For example, scheduled and blocked jobs are separate scopes.

```ruby
statuses = %i[pending failed in_progress blocked scheduled finished]
statuses.to_h { |status| [status, ActiveJob.jobs.public_send(status).count] }
```

Mission Control caps unlimited counts at `MissionControl::Jobs.internal_query_count_limit` (default 500,000). Above the cap, a count returns `Float::INFINITY`. Do not sum these values and call the result an exact total. An explicit `.limit(100).count` counts only that limited subset; it is not a way to obtain an unrestricted total.

## Count all retained Solid Queue rows

For the Solid Queue database configured in this application:

```ruby
SolidQueue::Job.count
SolidQueue::Job.where(queue_name: "default").count
SolidQueue::Job.where(class_name: "SomeJob").count

# These include every state, rather than only ready/pending jobs.
SolidQueue::Job.where(finished_at: nil).count
SolidQueue::Job.where.not(finished_at: nil).count

SolidQueue::Job.group(:queue_name).count
SolidQueue::Job.group(:class_name).count
```

Use `job_class_name:` with Mission Control; use the actual `class_name:` column with `SolidQueue::Job`.

These are persisted-row counts, **not lifetime totals**. Finished rows depend on `SolidQueue.preserve_finished_jobs` and subsequent cleanup. With preservation disabled, a successful completion removes its job row. With preservation enabled, an existing cleanup policy can still remove older finished rows. Keep your current retention configuration; a counting recipe cannot reconstruct deleted history.

Direct database counts can take longer on a large queue database. Separate queries can observe different moments while workers run; this example does not claim an atomic production snapshot. In a multi-server Mission Control console, confirm you selected the intended Solid Queue backend. The direct model queries use this application's configured Solid Queue database, not arbitrary remote adapters.

## Optional reusable recipe

[`counts.rb`](counts.rb) packages the reads above. Load it from a file you have reviewed in your own app:

```ruby
load "path/to/counts.rb"
QueueCounts.read
QueueCounts.read(queue_name: "default", job_class_name: "SomeJob")
```

It returns separate status counts and retained/unfinished/finished database-row counts. It preserves an `Infinity` result from Mission Control and does not change count limits or retention settings. It requires the active application's adapter to be Solid Queue.

## Verify in an isolated database

The fixture creates a fresh temporary SQLite database from Solid Queue's published schema. It enqueues ordinary test jobs, actually performs a successful and a failing job, and creates the remaining execution states through Solid Queue's lifecycle operations. It never starts a worker or connects to an existing application's database.

```sh
bundle install
bundle exec ruby verify.rb
```

Tested on Ruby 3.3.4, Rails 8.1.4.1, Mission Control Jobs 1.3.1, Solid Queue 1.7.2 and sqlite3 2.10.2. The original report used Ruby 4.0.7 and Rails 8.1.4; those exact runtime versions were not tested.

The fixture prints `PASS` for every check and finishes with:

```json
{
  "by_status": {
    "pending": 3,
    "failed": 1,
    "in_progress": 1,
    "blocked": 1,
    "scheduled": 1,
    "finished": 1
  },
  "retained_rows": 8,
  "unfinished_rows": 7,
  "finished_rows": 1
}
```

It also verifies class/queue filters, the original status-less errors, unchanged job records after reads, count-cap behavior, and completion with finished preservation disabled. Configuration changes happen only inside this temporary fixture process and are restored. This is a scripted database check; the original requester has not confirmed adoption.

## Sources

- [Original usage question](https://github.com/rails/mission_control-jobs/issues/348)
- [Mission Control 1.3.1 querying guide](https://github.com/rails/mission_control-jobs/blob/v1.3.1/README.md#console-helpers-scripting-and-dealing-with-big-sets-of-jobs)
- [Solid Queue adapter: statuses and count dispatch](https://github.com/rails/mission_control-jobs/blob/v1.3.1/lib/active_job/queue_adapters/solid_queue_ext.rb)
- [Mission Control count-cap configuration](https://github.com/rails/mission_control-jobs/blob/v1.3.1/README.md#other-configuration-settings)
- [Solid Queue finished-job behavior](https://github.com/rails/solid_queue/blob/v1.7.2/app/models/solid_queue/job/executable.rb)

## Optional coffee

This example is free. If it saved you some time and you would like to buy me a coffee, thank you—contributions are entirely optional.

- **USDC / SOL · Solana:** `9tY6D9mwcFaJwwzEHvw2v7nhSpdjqjNBYtuooyBN6rYy`
- **USDC / ETH · Base:** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
- **USDT · BNB Smart Chain (BEP20):** `0x568Ab98578d682FB0B0b45619BE73EbFfbf5a6eA`
