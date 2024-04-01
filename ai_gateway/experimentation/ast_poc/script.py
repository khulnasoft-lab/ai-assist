
if __name__ == "__main__":
    from src_files_finder import DirectoryTraversal, TreeSitterLanguage, TreeSitterParser
    from graph import GraphBuilder
    from concurrent.futures import ThreadPoolExecutor
    import sys
    import asyncio
    from gqlalchemy import Memgraph
    languages = [
      TreeSitterLanguage(name="javascript", extensions=[".js", ".jsx"], scmPath="tree-sitter-javascript-tags.scm"),
      TreeSitterLanguage(name="typescript", extensions=[".ts", ".tsx"], scmPath="tree-sitter-typescript-tags.scm"),
      TreeSitterLanguage(name="python", extensions=[".py"], scmPath="tree-sitter-python-tags.scm"),
      TreeSitterLanguage(name="ruby", extensions=[".rb"], scmPath="tree-sitter-ruby-tags.scm"),      
    ]

    tree_sitter_parser = TreeSitterParser(languages)
    directory_traversal = DirectoryTraversal(sys.argv[1], tree_sitter_parser)
    directory_traversal.get_relevant_files()
    all_files = directory_traversal.get_all_files_sorted_by_size()
    print('Total files:', len(all_files))
    executor = ThreadPoolExecutor()
    graph_builder = GraphBuilder(memgraph=Memgraph(host="127.0.0.1", port=7687), executor=executor, project_root_path=sys.argv[1])
    asyncio.run(graph_builder.update_graph_from_csv([file.path for file in all_files]))
    
    
              
    