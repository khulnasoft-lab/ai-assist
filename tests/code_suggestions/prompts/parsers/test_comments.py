import pytest

from ai_gateway.code_suggestions.processing.base import LanguageId
from ai_gateway.prompts.parsers import CodeParser
from ai_gateway.prompts.parsers.comments import BaseCommentVisitor

EMPTY_SOURCE_FILE = ""

C_SOURCE_SAMPLE_COMMENTS = """// foo
/* bar */
"""
C_SOURCE_SAMPLE_MIXED = """
#include<stdio.h>

// foo
int main()
{
    /*
      bar
    */
	return printf("\nHello World!");
}
"""

C_SOURCE_SAMPLE_ENDS_WITH_COMMENT = """
#include<stdio.h>

// foo
int main()
{
    /*
      bar
    */
	return printf("\nHello World!");
}
// bar
"""

CPP_SOURCE_SAMPLE_COMMENTS = """
// foo
/* bar */
"""
CPP_SOURCE_SAMPLE_MIXED = """
#include <iostream>

int main() {
  std::cout << "Hello world!\n";
}
"""
CPP_SOURCE_SAMPLE_ENDS_WITH_COMMENT = """
#include <iostream>

int main() {
  std::cout << "Hello world!\n";
}
/* bar */
"""

CSHARP_SOURCE_SAMPLE_COMMENTS = """
// foo
/* bar */
/// <summary>
///  C# also has XML comments
/// </summary>
"""
CSHARP_SOURCE_SAMPLE_MIXED = """
/// <summary>
///  This is a hello world program.
/// </summary>
namespace HelloWorld
{
    class Program
    {
        static void Main(string[] args)
        {
            System.Console.WriteLine("Hello world!");
        }
    }
}
"""
CSHARP_SOURCE_SAMPLE_ENDS_WITH_COMMENT = """
/// <summary>
///  This is a hello world program.
/// </summary>
namespace HelloWorld
{
    class Program
    {
        static void Main(string[] args)
        {
            System.Console.WriteLine("Hello world!");
        }
    }
}
/// do something else
"""

GO_SOURCE_SAMPLE_COMMENTS = """// foo
// bar
/*
func main(){

}
*/
"""

GO_SOURCE_SAMPLE_MIXED = """// the main package
package main

// The main function
func main() {

}
"""
GO_SOURCE_SAMPLE_ENDS_WITH_COMMENT = """// the main package
package main

// The main function
func main() {

}
// make another function here
"""

JAVA_SOURCE_SAMPLE_COMMENTS = """
// foo
/* bar */
/**
 *
 * foobar
 *
 */
"""
JAVA_SOURCE_SAMPLE_MIXED = """
public class HelloWorld
{
 // foo
 public static void main(String[] args)
 {
  /*
   bar
  */
  System.out.println("Hello world!");
 }
}
"""
JAVA_SOURCE_SAMPLE_ENDS_WITH_COMMENT = """
public class HelloWorld
{
 // foo
 public static void main(String[] args)
 {
  /*
   bar
  */
  System.out.println("Hello world!");
 }
}
// bar
"""

JS_SOURCE_SAMPLE_COMMENTS = """
// foo
/* bar */
"""
JS_SOURCE_SAMPLE_MIXED = """
// writes hello world
document.write("Hello world!");
"""
JS_SOURCE_SAMPLE_ENDS_WITH_COMMENT = """
// writes hello world
document.write("Hello world!");
// writes goodbye world
"""

PYTHON_SOURCE_SAMPLE_COMMENTS = """
# foo
"""
PYTHON_SOURCE_SAMPLE_MIXED = """
# this prints hello world
if __name__=="__main__":
    print(f"Hello world!")
"""
PYTHON_SOURCE_SAMPLE_ENDS_WITH_COMMENT = """
# this prints hello world
if __name__=="__main__":
    print(f"Hello world!")
# this prints goodbye world
"""

RUBY_SOURCE_SAMPLE_COMMENTS = """
# foo
=begin
multiline comment
=end
"""
RUBY_SOURCE_SAMPLE_MIXED = """
# this says hello world
puts "Hello world!"
"""
RUBY_SOURCE_SAMPLE_ENDS_WITH_COMMENT = """
# this says hello world
puts "Hello world!"
# this says goodbye world
"""

RUST_SOURCE_SAMPLE_COMMENTS = """
// foo
// bar
"""
RUST_SOURCE_SAMPLE_MIXED = """
// this says hello world
fn main() {
   println!("Hello world!");
}
"""
RUST_SOURCE_SAMPLE_ENDS_WITH_COMMENT = """
// this says hello world
fn main() {
   println!("Hello world!");
}
// this says goodbye world
"""

SCALA_SOURCE_SAMPLE_COMMENTS = """
// foo
/* bar */
/**Comment start
*
*foobar
*
*comment ends*/
"""
SCALA_SOURCE_SAMPLE_MIXED = """
// foo
println("Hello world!")
"""
SCALA_SOURCE_SAMPLE_ENDS_WITH_COMMENT = """
// foo
println("Hello world!")
// bar
"""

TS_SOURCE_SAMPLE_COMMENTS = """
// foo
/* bar */
/**
foobar
*/
"""
TS_SOURCE_SAMPLE_MIXED = """
// foo
let message: string = 'Hello, World!';
console.log(message);
"""
TS_SOURCE_SAMPLE_ENDS_WITH_COMMENT = """
// foo
let message: string = 'Hello, World!';
console.log(message);
// bar
"""

KOTLIN_SOURCE_SAMPLE_COMMENTS = """
// foo
/* bar */
/**
 *
 * foobar
 *
 */
"""
KOTLIN_SOURCE_SAMPLE_MIXED = """
// foo
fun main() {
    println("Hello world!")
}
"""
KOTLIN_SOURCE_SAMPLE_ENDS_WITH_COMMENT = """
// foo
fun main() {
    println("Hello world!")
}
// bar
"""


PHP_SOURCE_SAMPLE_COMMENTS = """
// This is a one-line c++ style comment
/*
This is a multi line comment
yet another line of comment
*/
"""


PHP_SOURCE_SAMPLE_MIXED = """
<?php
echo "Hello World!";
?>
"""


@pytest.mark.parametrize(
    ("lang_id", "source_code", "comments_only", "ends_with_comment"),
    [
        (LanguageId.C, C_SOURCE_SAMPLE_COMMENTS, True, True),
        (LanguageId.C, C_SOURCE_SAMPLE_MIXED, False, False),
        (LanguageId.C, C_SOURCE_SAMPLE_ENDS_WITH_COMMENT, False, True),
        (LanguageId.CPP, CPP_SOURCE_SAMPLE_COMMENTS, True, True),
        (LanguageId.CPP, CPP_SOURCE_SAMPLE_MIXED, False, False),
        (LanguageId.CPP, CPP_SOURCE_SAMPLE_ENDS_WITH_COMMENT, False, True),
        (LanguageId.CSHARP, CSHARP_SOURCE_SAMPLE_COMMENTS, True, True),
        (LanguageId.CSHARP, CSHARP_SOURCE_SAMPLE_MIXED, False, False),
        (LanguageId.CSHARP, CSHARP_SOURCE_SAMPLE_ENDS_WITH_COMMENT, False, True),
        (LanguageId.GO, GO_SOURCE_SAMPLE_COMMENTS, True, True),
        (LanguageId.GO, GO_SOURCE_SAMPLE_MIXED, False, False),
        (LanguageId.GO, GO_SOURCE_SAMPLE_ENDS_WITH_COMMENT, False, True),
        (LanguageId.JAVA, JAVA_SOURCE_SAMPLE_COMMENTS, True, True),
        (LanguageId.JAVA, JAVA_SOURCE_SAMPLE_MIXED, False, False),
        (LanguageId.JAVA, JAVA_SOURCE_SAMPLE_ENDS_WITH_COMMENT, False, True),
        (LanguageId.JS, JS_SOURCE_SAMPLE_COMMENTS, True, True),
        (LanguageId.JS, JS_SOURCE_SAMPLE_MIXED, False, False),
        (LanguageId.JS, JS_SOURCE_SAMPLE_ENDS_WITH_COMMENT, False, True),
        (LanguageId.PYTHON, PYTHON_SOURCE_SAMPLE_COMMENTS, True, True),
        (LanguageId.PYTHON, PYTHON_SOURCE_SAMPLE_MIXED, False, False),
        (LanguageId.PYTHON, PYTHON_SOURCE_SAMPLE_ENDS_WITH_COMMENT, False, True),
        (LanguageId.RUBY, RUBY_SOURCE_SAMPLE_COMMENTS, True, True),
        (LanguageId.RUBY, RUBY_SOURCE_SAMPLE_MIXED, False, False),
        (LanguageId.RUBY, RUBY_SOURCE_SAMPLE_ENDS_WITH_COMMENT, False, True),
        (LanguageId.RUST, RUST_SOURCE_SAMPLE_COMMENTS, True, True),
        (LanguageId.RUST, RUST_SOURCE_SAMPLE_MIXED, False, False),
        (LanguageId.RUST, RUST_SOURCE_SAMPLE_ENDS_WITH_COMMENT, False, True),
        (LanguageId.SCALA, SCALA_SOURCE_SAMPLE_COMMENTS, True, True),
        (LanguageId.SCALA, SCALA_SOURCE_SAMPLE_MIXED, False, False),
        (LanguageId.SCALA, SCALA_SOURCE_SAMPLE_ENDS_WITH_COMMENT, False, True),
        (LanguageId.TS, TS_SOURCE_SAMPLE_COMMENTS, True, True),
        (LanguageId.TS, TS_SOURCE_SAMPLE_MIXED, False, False),
        (LanguageId.TS, TS_SOURCE_SAMPLE_ENDS_WITH_COMMENT, False, True),
        (LanguageId.KOTLIN, KOTLIN_SOURCE_SAMPLE_COMMENTS, True, True),
        (LanguageId.KOTLIN, KOTLIN_SOURCE_SAMPLE_MIXED, False, False),
        (LanguageId.KOTLIN, KOTLIN_SOURCE_SAMPLE_ENDS_WITH_COMMENT, False, True),
        (LanguageId.PHP, PHP_SOURCE_SAMPLE_COMMENTS, False, False),
        (LanguageId.PHP, PHP_SOURCE_SAMPLE_MIXED, False, False),
    ],
)
def test_comments(
    lang_id: LanguageId, source_code: str, comments_only: bool, ends_with_comment: bool
):
    parser = CodeParser.from_language_id(source_code, lang_id)

    assert parser.comments_only() == comments_only
    assert parser.ends_with_comment() == ends_with_comment
