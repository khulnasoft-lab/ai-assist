require 'faye/websocket'
require 'eventmachine'
require 'benchmark'
require 'net/http'
require 'net/http/persistent'

REQUEST_COUNT = 10_000
REQ_DATA = {
  current_file: {
    file_name: "test.py",
    content_above_cursor: "#create hello world function",
    content_below_cursor: ""
  }
}

def websocket
  puts "running websocket"

  EM.run do
    ws = Faye::WebSocket::Client.new('ws://127.0.0.1:5052/v2/code/completions/ws')

    counter = 0

    ws.on :open do |event|
      p [:open]
      ws.send(REQ_DATA.to_s)
    end

    ws.on :error do |event|
      p [:error, event]
    end

    ws.on :message do |event|
      p [:message, event.data]

      counter += 1
      if counter < REQUEST_COUNT
        puts "sending #{counter}"
        ws.send(REQ_DATA.to_s)
      else
        ws.close
      end
    end

    ws.on :close do |event|
      p [:close, event.code, event.reason]
      EM.stop_event_loop
    end
  end
end

def keepalive
  puts "running http keepalive"

  uri = URI('http://127.0.0.1:5052/v2/code/completions')
  req = Net::HTTP::Post.new(uri)
  req.set_form_data REQ_DATA

  Net::HTTP.start(uri.host, uri.port) do |http|
    REQUEST_COUNT.times do |idx|
      puts "sending #{idx}"
      http.request(req)
    end
  end
end

http_time = Benchmark.measure { keepalive }
bm_time = Benchmark.measure { websocket }

puts "http total (#{REQUEST_COUNT}):"
puts http_time
puts "websocket total (#{REQUEST_COUNT}):"
puts bm_time

