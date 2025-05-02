import glob
import re

def Deline(lines):
    result = []
    previous_line = ''
    for line in lines:
        
        if (line.startswith('![') and is_empty_line(previous_line)) :
            print("----")
            print(line)
        else:
            result.append(previous_line)

        previous_line = line

    result.append(previous_line)
    return result

def is_empty_line(line):
    return len(line.strip()) == 0

if __name__ == '__main__':
    for md in glob.glob("./*.md"):
        print("Process:" + str(md))
        lines = []
        with open(md, 'r') as f:
            lines = f.readlines()
        result = Deline(lines)
        with open(md, 'w') as f:
            f.writelines(result)