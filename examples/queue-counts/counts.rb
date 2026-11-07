# Load inside an application that already uses Mission Control and Solid Queue.
# Every operation below is a read. Separate queries are not an atomic snapshot.
module QueueCounts
  STATUSES = %i[pending failed in_progress blocked scheduled finished].freeze

  def self.read(queue_name: nil, job_class_name: nil)
    adapter = ActiveJob::Base.queue_adapter
    unless adapter.is_a?(ActiveJob::QueueAdapters::SolidQueueAdapter)
      raise ArgumentError, "This recipe requires the application's Solid Queue adapter"
    end

    queue_name = queue_name.to_s.presence
    job_class_name = job_class_name.to_s.presence
    jobs = ActiveJob.jobs.where(queue_name: queue_name, job_class_name: job_class_name)

    rows = SolidQueue::Job.all
    rows = rows.where(queue_name: queue_name) unless queue_name.nil?
    rows = rows.where(class_name: job_class_name) unless job_class_name.nil?

    {
      by_status: STATUSES.to_h { |status| [status, jobs.public_send(status).count] },
      retained_rows: rows.count,
      unfinished_rows: rows.where(finished_at: nil).count,
      finished_rows: rows.where.not(finished_at: nil).count
    }
  end
end
