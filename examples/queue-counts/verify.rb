require "bundler/setup"
require "tmpdir"
require "json"
require "logger"

# This fixture never opens the host application's database or starts a worker.
Dir.mktmpdir("queue-counts-") do |directory|
  ENV["RAILS_ENV"] = "test"
  ENV["DATABASE_URL"] = "sqlite3:#{File.join(directory, 'queue.sqlite3')}"

  require "rails/all"
  require "propshaft"
  require "solid_queue"
  require "mission_control/jobs"

  class QueueCountsFixture < Rails::Application
    config.load_defaults 8.1
    config.eager_load = false
    config.logger = Logger.new(File::NULL)
    config.active_job.queue_adapter = :solid_queue
    config.secret_key_base = "temporary-fixture-only" * 8
  end

  QueueCountsFixture.config.root = directory
  QueueCountsFixture.initialize!
  ActiveRecord::Base.establish_connection(adapter: "sqlite3", database: File.join(directory, "queue.sqlite3"))
  ActiveRecord::Schema.verbose = false
  load File.join(Gem.loaded_specs.fetch("solid_queue").full_gem_path, "lib/generators/solid_queue/install/templates/db/queue_schema.rb")
  ActiveJob::Base.logger = Logger.new(File::NULL)
  SolidQueue.logger = Logger.new(File::NULL)

  class ReadableJob < ActiveJob::Base
    class_attribute :performed, default: []
    def perform(label)
      self.class.performed += [label]
    end
  end

  class BrokenJob < ActiveJob::Base
    def perform
      raise "expected fixture failure"
    end
  end

  class SerialJob < ActiveJob::Base
    limits_concurrency to: 1, key: ->(key) { key }, duration: 1.hour
    def perform(key); end
  end

  def check(condition, description)
    raise "FAIL: #{description}" unless condition
    puts "PASS: #{description}"
  end

  process = SolidQueue::Process.create!(kind: "Worker", name: "fixture", pid: Process.pid,
    hostname: "localhost", last_heartbeat_at: Time.current)
  def claim(queue_name, process)
    SolidQueue::ReadyExecution.claim([queue_name], 1, process.id).fetch(0)
  end

  ReadableJob.set(queue: "alpha").perform_later("ready-alpha")
  ReadableJob.set(queue: "beta").perform_later("ready-beta")
  ReadableJob.set(queue: "alpha", wait: 1.hour).perform_later("scheduled")
  SerialJob.set(queue: "serial").perform_later("same")
  SerialJob.set(queue: "serial").perform_later("same")
  ReadableJob.set(queue: "running").perform_later("running")
  claim("running", process)
  BrokenJob.set(queue: "failure").perform_later
  begin
    claim("failure", process).perform
  rescue RuntimeError => error
    raise unless error.message == "expected fixture failure"
  end
  ReadableJob.set(queue: "completion").perform_later("finished")
  claim("completion", process).perform

  expected = { pending: 3, failed: 1, in_progress: 1, blocked: 1, scheduled: 1, finished: 1 }
  check(ReadableJob.performed == ["finished"], "the finished fixture really executed")
  expected.each do |status, count|
    check(ActiveJob.jobs.public_send(status).count == count, "real #{status} count is #{count}")
  end
  [ActiveJob.jobs, ActiveJob.jobs.where(queue_name: "alpha")].each do |relation|
    check(relation.inspect.include?("loaded: false"), "root relation can be constructed without a query")
    begin
      relation.count
      raise "status-less count unexpectedly succeeded"
    rescue ActiveJob::Errors::QueryError => error
      check(error.message.include?("Status not supported:"), "status-less count reproduces issue348")
    end
  end

  # The recipe must produce real query results, rather than replace the adapter.
  require_relative "counts"
  before = SolidQueue::Job.order(:id).map { |job| [job.id, job.status, job.attributes] }
  report = QueueCounts.read
  check(report.fetch(:by_status) == expected, "recipe returns all six status counts")
  check(report.fetch(:retained_rows) == 8, "all-status retained-row count is8")
  check(report.fetch(:unfinished_rows) == 7, "unfinished includes scheduled, blocked, claimed and failed")
  check(report.fetch(:finished_rows) == 1, "finished count reflects retained rows")
  filtered = QueueCounts.read(queue_name: "alpha", job_class_name: "ReadableJob")
  check(filtered.fetch(:retained_rows) == 2, "all-status queue and class filter works")
  check(filtered.fetch(:by_status) == expected.transform_values { 0 }.merge(pending: 1, scheduled: 1),
    "status scopes keep the same queue and class filters")
  check(ActiveJob.jobs.failed.where(job_class_name: "BrokenJob").count == 1, "failed class filter works")
  check(ActiveJob.jobs.failed.where(queue_name: "alpha").count == 0, "failed queue filter excludes other queues")
  listed = ActiveJob.jobs.failed.where(queue_name: "failure", job_class_name: "BrokenJob").limit(10).to_a
  check(listed.length == 1 && listed.first.status == :failed,
    "explicit status also lists the requested failed job")
  check(SolidQueue::Job.group(:class_name).count == { "ReadableJob" => 5, "SerialJob" => 2, "BrokenJob" => 1 },
    "retained-row grouping returns native database counts")
  check(before == SolidQueue::Job.order(:id).map { |job| [job.id, job.status, job.attributes] },
    "all recipe reads leave job rows and statuses unchanged")

  previous_limit = MissionControl::Jobs.internal_query_count_limit
  begin
    MissionControl::Jobs.internal_query_count_limit = 2
    check(QueueCounts.read.fetch(:by_status).fetch(:pending).infinite?, "capped count remains Infinity")
    check(ActiveJob.jobs.pending.limit(2).count == 2, "an explicit limit counts only its limited subset")
    check(QueueCounts.read.fetch(:retained_rows) == 8, "direct retained-row count is independent of the cap")
  ensure
    MissionControl::Jobs.internal_query_count_limit = previous_limit
  end

  previous_retention = SolidQueue.preserve_finished_jobs
  begin
    SolidQueue.preserve_finished_jobs = false
    ephemeral = ReadableJob.set(queue: "ephemeral").perform_later("not-retained")
    claim("ephemeral", process).perform
    check(ReadableJob.performed == ["finished", "not-retained"], "non-retained fixture also really executed")
    check(!SolidQueue::Job.exists?(id: ephemeral.provider_job_id), "host retention=false removes the new completed row")
    check(QueueCounts.read.fetch(:retained_rows) == 8 && QueueCounts.read.fetch(:finished_rows) == 1,
      "counts retain existing history but cannot recover deleted completions")
  ensure
    SolidQueue.preserve_finished_jobs = previous_retention
  end

  puts JSON.pretty_generate(versions: %w[rails mission_control-jobs solid_queue sqlite3].to_h { |name|
    [name, Gem.loaded_specs.fetch(name).version.to_s]
  }, ruby: RUBY_VERSION, report: report)
  ActiveRecord::Base.connection_pool.disconnect!
end
