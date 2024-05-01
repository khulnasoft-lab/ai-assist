# frozen_string_literal: true

module Gitlab
  module Llm
    module Embeddings
      module Utils
        class DocsContentParser < BaseContentParser
          MAX_CHARS_PER_EMBEDDING = 1500
          MIN_CHARS_PER_EMBEDDING = 100

          def self.parse_and_split(content, source_name, source_type, root_url:)
            parser = new(MIN_CHARS_PER_EMBEDDING, MAX_CHARS_PER_EMBEDDING, root_url: root_url)

            parser.parse_and_split(content, source_name, source_type)
          end
        end
      end
    end
  end
end
