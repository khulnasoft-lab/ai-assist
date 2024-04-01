import os
from typing import List, Dict,Sequence, Union
from git import Repo


class FinalFile:
    def __init__(self, path: str, size: int):
        self.path = path
        self.size = size

class TreeSitterLanguage:
  name: str
  extensions: List[str]
  wasmPath: str
  
  def __init__(self, name: str, extensions: List[str], wasmPath: str):
    self.name = name
    self.extensions = extensions
    self.wasmPath = wasmPath

class TreeSitterParser:
  def __init__(self, languages: List[TreeSitterLanguage]):
    self.languages: Dict[str, TreeSitterLanguage] = { ext:  lang for lang in languages for ext in lang.extensions}

  def get_tree_sitter_language_for_file(self, filename: str) ->  TreeSitterLanguage | None:
    _, ext = os.path.splitext(filename)
    return self.languages.get(ext)

class DirectoryTraversal:
    def __init__(self, repo_path: str, tree_sitter_parser: TreeSitterParser):
        self.repo = Repo(repo_path)
        self.tree_sitter_parser = tree_sitter_parser
        self.final_files: List[FinalFile] = []

    def get_relevant_files(self) -> None:
        for item in self.repo.tree().traverse():
            if item.type == "blob":
                file_path = os.path.join(self.repo.working_dir, item.path)
                if self.tree_sitter_parser.get_tree_sitter_language_for_file(file_path):
                    self.final_files.append(FinalFile(file_path, item.size))

        self.final_files.sort(key=lambda file: file.size, reverse=True)

    def get_all_files_sorted_by_size(self) -> List[FinalFile]:
        return self.final_files


if __name__ == "__main__":
    from repo_map_builder import RepoMap
    import sys
    languages = [
      TreeSitterLanguage(name="javascript", extensions=[".js", ".jsx"], wasmPath="tree-sitter-javascript.wasm"),
      TreeSitterLanguage(name="typescript", extensions=[".ts", ".tsx"], wasmPath="tree-sitter-typescript.wasm"),
      TreeSitterLanguage(name="python", extensions=[".py"], wasmPath="tree-sitter-python.wasm"),
      TreeSitterLanguage(name="ruby", extensions=[".rb"], wasmPath="tree-sitter-ruby.wasm"),      
      # Add more languages and their extensions as needed
    ]

    tree_sitter_parser = TreeSitterParser(languages)
    directory_traversal = DirectoryTraversal(sys.argv[1], tree_sitter_parser)
    directory_traversal.get_relevant_files()
    all_files = directory_traversal.get_all_files_sorted_by_size()
    
    class IO:
      def read_text(self, filename: str) -> str:
          with open(str(filename), "r", encoding='utf8') as f:
                return f.read()
      def tool_output(self, msg: str) -> None:
          print(msg)
      def tool_error(self, msg: str) -> None:
          print(msg)
       
              
    repo_map = RepoMap(
      io=IO(),
      verbose=True,
    )
    
    print("files length : ", len(all_files))
    
    ranked_tags = repo_map.get_repo_map([sys.argv[2]],( file.path for file in all_files))
    print(ranked_tags)
    # print(type(ranked_tags))




