from graph import GraphBuilder
import asyncio
from gqlalchemy import Memgraph
from ai_gateway.experimentation.ast_poc.tag_builder import TagsBuilder, Tag
from concurrent.futures import ThreadPoolExecutor

def create_chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


if __name__ == "__main__":
    from src_files_finder import (
        DirectoryTraversal,
        TreeSitterLanguage,
        TreeSitterParser,
    )
    from graph import GraphBuilder
    from concurrent.futures import ThreadPoolExecutor
    import sys
    import asyncio
    from gqlalchemy import Memgraph
    from tag_builder import Tag, TagsBuilder

    languages = [
        TreeSitterLanguage(
            name="javascript",
            extensions=[".js", ".jsx"],
            scmPath="tree-sitter-javascript-tags.scm",
        ),
        TreeSitterLanguage(
            name="typescript",
            extensions=[".ts", ".tsx"],
            scmPath="tree-sitter-typescript-tags.scm",
        ),
        TreeSitterLanguage(
            name="python", extensions=[".py"], scmPath="tree-sitter-python-tags.scm"
        ),
        TreeSitterLanguage(
            name="ruby", extensions=[".rb"], scmPath="tree-sitter-ruby-tags.scm"
        ),
    ]

    tree_sitter_parser = TreeSitterParser(languages)
    directory_traversal = DirectoryTraversal(sys.argv[1], tree_sitter_parser)
    directory_traversal.get_relevant_files()
    all_files = directory_traversal.get_all_files_sorted_by_size()
    print("Total files:", len(all_files))
    executor = ThreadPoolExecutor(max_workers=1000)
    graph_builder = GraphBuilder(
        memgraph=Memgraph(host="127.0.0.1", port=7687),
        tags_builder=TagsBuilder(),
        project_root_path=sys.argv[1]
    )
    
    asyncio.run(graph_builder.update_graph_from_csv([file.path for file in all_files], executor))
    # chunks = list(create_chunks([file.path for file in all_files], n=len(all_files) // 32))

    # async def update_graph_concurrently():
    #     total_chunks = len(chunks)
    #     completed_chunks = 0

    #     async def process_chunk(chunk):
    #         nonlocal completed_chunks
    #         await graph_builder.update_graph_in_batches(file_paths=chunk, executor=executor)
    #         completed_chunks += 1
    #         print(f"Completed chunk {completed_chunks}/{total_chunks} - {completed_chunks/total_chunks*100:.2f}%")

    #     tasks = [asyncio.create_task(process_chunk(chunk)) for chunk in chunks]
    #     await asyncio.gather(*tasks)

    # asyncio.run(update_graph_concurrently())