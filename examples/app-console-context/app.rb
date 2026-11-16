# frozen_string_literal: true

class Counter
  attr_reader :value

  def initialize(value)
    @value = value
  end

  def add(amount)
    @value += amount
  end

  def doubled
    @value * 2
  end
end

def run_console(twice: false)
  require "irb"

  app = Counter.new(2)
  local_note = "ready"
  sessions = twice ? 2 : 1

  sessions.times do |index|
    puts "CONSOLE session=#{index + 1}"
    binding.irb(show_code: false)
    puts "RESUMED session=#{index + 1} value=#{app.value} note=#{local_note} argv=#{ARGV.inspect}"
  end

  puts "COMPLETE value=#{app.value} note=#{local_note} argv=#{ARGV.inspect}"
end

case ARGV.first
when "console"
  run_console(twice: ARGV.include?("--twice"))
when "status"
  app = Counter.new(2)
  puts "STATUS value=#{app.value} doubled=#{app.doubled}"
else
  warn "Usage: ruby app.rb status | console [--twice] [extra app arguments]"
  exit 1
end
