

import os
import sys


def main(args: list[str]) -> None:

    for file in os.listdir('trace/templates'):
        if not file.endswith('_template.bt'):
            continue

        template_path = os.path.join('trace', 'templates', file)
        output_path = os.path.join('trace', 'run', 'scripts', file.replace('_template', ''))
        
    
        with open(template_path, 'r') as fin:
            open_template = fin.read()
            processes_condition = "".join([f'comm == "{arg}" || ' for arg in args]) + "false"
            open_template = open_template.replace('[TEMPLATE_PROCESS_NAMES]', processes_condition)

        with open(output_path, 'w') as fout:
            fout.write(open_template)


if __name__ == "__main__":

    args = sys.argv[1].split(',')
    main(args)