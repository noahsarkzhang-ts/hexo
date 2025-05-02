import glob
import re

def Convert(lines):
    result = []
    previous_line = ''
    for line in lines:
        result.append(previous_line)
        if (line.startswith('* ') and not previous_line.startswith('* ')) \
           or (line.startswith('> ') and not previous_line.startswith('> ')) \
           or (line.startswith('- ') and not previous_line.startswith('- ') and not previous_line.startswith('tags:')) \
           or (line.startswith('{% blockquote') and not previous_line.startswith('{% blockquote')) \
           or (re.match('^\d\.', line) and not re.match('^\d\.', previous_line)):
            result.append('\n')
            print ("---")
            print (previous_line)
            print (line)
        previous_line = line
    result.append(previous_line)
    return result

if __name__ == '__main__':
    for md in glob.glob("./*.md"):
        print("Process:" + str(md))
        lines = []
        with open(md, 'r') as f:
            lines = f.readlines()
        result = Convert(lines)
        with open(md, 'w') as f:
            f.writelines(result)