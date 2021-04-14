import os
import sys
import argparse
from jinja2 import Environment, FileSystemLoader, meta

def get_args():
    '''
    Parses the commandline args
    '''

    parser = argparse.ArgumentParser()

    parser.add_argument('-i', '--input', \
        required = True, \
        dest = 'input_conf',
        help = 'Path to the input configuration file.'
    )

    parser.add_argument('-o', '--output', \
        required = True, \
        dest = 'output_conf',
        help = 'Path to the completed output configuration file.'
    )
    return parser.parse_args()


def check_vars(required_vars):
    '''
    Given a set of strings, look for those in the
    environment variables. If not found or unset,
    then exit
    '''
    d = {}
    for v in required_vars:
        try:
            x = os.environ[v]
            if len(x) > 0:
                d[v] = x
            else:
                print('The environment variable {v} had '
                    'zero length. Stopping.'.format(v=v))
                sys.exit(1)
        except KeyError as ex:
            print('We require the {v} environment variable to be set.'.format(v=v))
            sys.exit(1)
    return d


def fill(args):
    template_dir = os.path.dirname(args.input_conf)
    env = Environment(loader=FileSystemLoader(template_dir))
    parsed_content = env.parse(
        open(os.path.basename(args.input_conf)).read())
    required_vars = meta.find_undeclared_variables(parsed_content)
    env_vars_dict = check_vars(required_vars)
    template = env.get_template(args.input_conf)
    final_txt = template.render(env_vars_dict)

    with open(args.output_conf, 'w') as fout:
        fout.write(final_txt)


if __name__ == '__main__':
    args = get_args()
    fill(args)