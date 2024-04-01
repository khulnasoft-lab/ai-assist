import os
from typing import List, Dict, Tuple
from git import Repo

class FinalFile:
    def __init__(self, path: str, size: int):
        self.path = path
        self.size = size

class TreeSitterLanguage:
  name: str
  extensions: List[str]
  scmPath: str
  
  def __init__(self, name: str, extensions: List[str], scmPath: str):
    self.name = name
    self.extensions = extensions
    self.scmPath = scmPath

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
                if self.tree_sitter_parser.get_tree_sitter_language_for_file(file_path) and not self.is_test_file(file_path):
                    self.final_files.append(FinalFile(file_path, item.size))

        self.final_files.sort(key=lambda file: file.size, reverse=True)

    def get_all_files_sorted_by_size(self) -> List[FinalFile]:
        return self.final_files
      
    def is_test_file(self, file_path: str) -> bool:
        # Define file extensions and test file patterns for each language
        language_patterns: Dict[str, List[str]] = {
            ".rb": ["_test.rb", "_spec.rb"],
            ".js": ["test.js", ".test.js", ".spec.js"],
            ".py": ["test_", "_test.py"],
            ".ts": ["test.ts", ".test.ts", ".spec.ts"],
        }

        # Extract the file extension from the file path
        file_extension: str = "." + file_path.split(".")[-1]

        # Check if the file extension exists in the language patterns dictionary
        if file_extension in language_patterns:
            patterns: List[str] = language_patterns[file_extension]
            # Check if the file name matches any test file pattern for the language
            for pattern in patterns:
                if pattern.startswith("."):
                    if file_path.endswith(pattern):
                        return True
                else:
                    if pattern in file_path:
                        return True

        # Return False if the file is not recognized as a test file
        return False






