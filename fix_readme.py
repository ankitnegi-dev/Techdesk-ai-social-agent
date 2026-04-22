import re

# Read the file
with open('README.md', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix MD012: Multiple consecutive blank lines - reduce to single blank
content = re.sub(r'\n\n\n+', '\n\n', content)

# Fix MD025 and MD001: Convert all # (except the first one) to ##
lines = content.split('\n')
first_h1_found = False
fixed_lines = []

for line in lines:
    if line.startswith('# ') and not first_h1_found:
        first_h1_found = True
        fixed_lines.append(line)
    elif line.startswith('# ') and first_h1_found:
        # Convert # to ##
        fixed_lines.append('## ' + line[2:])
    else:
        fixed_lines.append(line)

content = '\n'.join(fixed_lines)

# Fix MD040: Add language specs to code blocks
content = re.sub(r'```\n(┌|│|\s|[A-Z])', r'```text\n\1', content)

# Fix MD004 and MD032: Change dashes to asterisks in lists
# Replace "- " with "* " but be careful with the context
lines = content.split('\n')
fixed_lines = []
for line in lines:
    # Only replace list items (lines starting with dash after optional whitespace)
    if re.match(r'^- ', line):
        line = re.sub(r'^- ', '* ', line)
    fixed_lines.append(line)

content = '\n'.join(fixed_lines)

# Fix MD036: Change bold emphasis to heading
content = re.sub(r'\n\*\*([^*]+)\*\*\n', r'\n## \1\n', content)

# Write back
with open('README.md', 'w', encoding='utf-8') as f:
    f.write(content)

print("README.md fixed successfully!")
