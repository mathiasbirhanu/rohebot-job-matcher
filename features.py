import os
import subprocess

def make_and_push_commits(num_commits=500, filename="auto_commit.txt", repo_url="https://github.com/mathiasbirhanu/rohebot-job-matcher.git"):
    # 1. Initialize Git repository if not already initialized
    if not os.path.exists(".git"):
        subprocess.run(["git", "init"], check=True)
        print("Initialized a new Git repository.")

    # 2. Set default branch to main
    subprocess.run(["git", "branch", "-M", "main"], check=True)

    print(f"Starting creation of {num_commits} local commits...")

    # 3. Create commits in a loop
    for i in range(1, num_commits + 1):
        with open(filename, "a") as f:
            f.write(f"Automated commit entry #{i}\n")

        subprocess.run(["git", "add", filename], check=True, stdout=subprocess.DEVNULL)
        commit_message = f"Auto commit: update #{i}"
        subprocess.run(["git", "commit", "-m", commit_message], check=True, stdout=subprocess.DEVNULL)

        if i % 50 == 0 or i == num_commits:
            print(f"Progress: {i}/{num_commits} commits created.")

    print("\nAll local commits completed successfully!")

    # 4. Check if remote origin already exists, add it if not
    try:
        subprocess.run(["git", "remote", "get-url", "origin"], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Remote 'origin' already exists.")
    except subprocess.CalledProcessError:
        print(f"Adding remote repository: {repo_url}")
        subprocess.run(["git", "remote", "add", "origin", repo_url], check=True)

    # 5. Push all commits to GitHub automatically
    print("Pushing commits to GitHub... (You may be prompted for your GitHub credentials/token)")
    subprocess.run(["git", "push", "-u", "origin", "main"], check=True)
    print("Successfully pushed all 500 commits to GitHub!")

if __name__ == "__main__":
    make_and_push_commits()