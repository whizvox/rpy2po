import sys

from rpy2po import clitool

parser = clitool.get_argument_parser()
clitool.main(vars(parser.parse_args(sys.argv[1:])))
