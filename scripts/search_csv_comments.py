import subprocess

cmd = ["git", "log", "--grep=comment", "--oneline", "-n", "20"]
p = subprocess.run(cmd, cwd="/tmp/csv_test", capture_output=True, text=True)
print(p.stdout)
