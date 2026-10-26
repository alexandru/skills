---
name: external-research
description: "Researches evidence unavailable locally: external documentation, public repositories at specific refs, archives, and published dependency artifacts (JARs, source JARs, POMs, dependency graphs), reusing a persistent cache of Git clones and Maven artifacts. Use for library docs, upstream source and history, dependency source or metadata, or any question needing external evidence."
---

# External research

Choose the smallest reliable approach by accuracy, token cost, request cost, and elapsed time. Reassess only when evidence is missing or unreliable; do not repeat equivalent retrieval without a concrete reason or inspect related repositories/dependencies unless needed.

## Approaches

Options, cheapest to most expensive:

1. `glob`, `grep`, `read`, and shell filters for local inspection.
2. LSP/MCP/IDE semantic tools (IntelliJ IDEA, Metals LSP).
3. The `cellar` skill, when available, for JVM dependency public APIs.
4. `gh` and `az` read-only subcommands for GitHub and Azure queries.
5. `webfetch` for a known URL.
6. `websearch` when no URL is known (tool or skill, whatever is available).
7. `git ls-remote` for refs, then cached Git clones for source and history.
8. Maven, Gradle, sbt, npm metadata, and archive tools for published packages.

Rules:

- Use optional skills, such as `cellar`, when available; otherwise proceed with the tools that are available.
- For public API lookups of JVM dependencies, prefer the `cellar` skill when it is available and can answer directly.
- Do not use mutating `gh` or `az` subcommands; report the limitation.
- If a known web page answers directly, use `webfetch` and cite its URL; no task directory is needed. If content is empty, stale, or incomplete, switch only to a source likely to supply the missing evidence.
- For multi-file source research, use a cached checkout or fetch the required ref once; never crawl files over HTTP/API. Stop on access failures or throttling.
- For semantic questions, compilation, or linting, use an available LSP/MCP/IDE semantic tool (IntelliJ IDEA, Metals LSP) when it answers directly or produces relevant diagnostics, and cite the symbol or source location; clone or fetch only when its evidence is unavailable or insufficient.

## Persistent research cache

- Use `$HOME/.agents/librarian/` as a persistent cache across runs, sessions, and harnesses. Create it when needed; do not use the session directory or `mktemp` for research caching.
- Use absolute paths. Every repository cache directory must use `$HOME/.agents/librarian/repos/<organization>/<project-name>/`; the organization/project-name layout is mandatory, for example `typelevel/cats-effect` or `anomalyco/opencode`. Keep Maven repositories below `$HOME/.agents/librarian/maven/<library-key>/`.
- Before any network operation, inspect the relevant cache path. Reuse an existing matching clone, worktree, POM, JAR, source JAR, metadata file, or graph output. Download or fetch only the missing ref or artifact, or when the caller explicitly requests fresh remote data.
- Verify cache identity before reuse. For repositories, compare `git -C <base-clone> remote get-url origin` with the requested URL. If the URL differs, report the exact `<base-clone>` path and stop; do not overwrite it, reclone it, or select another cache destination.
- Cache maintenance may update Git metadata, add worktrees, and download artifacts, but must not modify source files, commit, push, change remotes, or alter the user's workspace.

## Clone and worktree workflow

For each organization/project-name path, the permanent base clone is named `main` and checks out the repository's default branch; requested refs belong in sibling worktrees.

For `https://github.com/typelevel/cats-effect/` at tag `v3.7.0`, follow these steps exactly:

Default to shallow, ref-scoped clones and fetches. Deepen the existing cache only when history is needed. Set a timeout of at least 10 minutes from the first attempt; run long transfers in the background.

1. Create the persistent repository directory:

   ```sh
   mkdir -p "$HOME/.agents/librarian/repos"
   mkdir -p "$HOME/.agents/librarian/repos/typelevel/cats-effect"
   ```

2. Check whether `$HOME/.agents/librarian/repos/typelevel/cats-effect/main` already exists. If it does, inspect its remote and worktree list; do not run `git clone` again. If it does not, shallow-clone the default branch:

   ```sh
   git clone --depth 1 --single-branch https://github.com/typelevel/cats-effect/ "$HOME/.agents/librarian/repos/typelevel/cats-effect/main"
   ```

3. Check whether `v3.7.0` is already available in the base clone and whether `$HOME/.agents/librarian/repos/typelevel/cats-effect/v3.7.0` is already registered by `git worktree list --porcelain`. If that worktree exists, reuse it without fetching or adding another one.

4. If the tag is missing, fetch only that tag. Do not fetch the repository on every repeated request:

   ```sh
   git -C "$HOME/.agents/librarian/repos/typelevel/cats-effect/main" fetch --depth 1 origin "refs/tags/v3.7.0:refs/tags/v3.7.0"
   ```

5. If the tag is available but its worktree is missing, create the sibling worktree and inspect it:

   ```sh
   git -C "$HOME/.agents/librarian/repos/typelevel/cats-effect/main" worktree add "$HOME/.agents/librarian/repos/typelevel/cats-effect/v3.7.0" v3.7.0
   # Inspect with glob, grep, read, or git -C "$HOME/.agents/librarian/repos/typelevel/cats-effect/v3.7.0" ...
   ```

   This is equivalent to running `git worktree add ../v3.7.0 v3.7.0` from the `main` worktree, but absolute paths avoid dependence on Bash's current directory.

6. For a branch, use the same process. Single-branch clones do not track other branches, so when the remote-tracking ref is absent, fetch it with `git -C "$HOME/.agents/librarian/repos/typelevel/cats-effect/main" fetch --depth 1 origin "refs/heads/<branch>:refs/remotes/origin/<branch>"`. Then add a sibling worktree. If a local branch must be created from a remote-tracking branch, use `git worktree add -b "<branch>" "<absolute-worktree-path>" "origin/<branch>"`.

7. If a requested path exists but is not a registered worktree, or its remote does not match, do not overwrite it. Report the exact path and stop; do not select another cache destination.

Do not use `git checkout` or switch the base clone's branch to inspect a ref. Do not run `git worktree remove`, `git worktree prune`, `git reset`, `git clean`, or any command that changes source files. Do not push or change a remote.

If cloning, fetching, or adding a worktree fails, report the exact error. Do not retry with a different destination or reclone the same repository.

## Maven artifact workflow

- For a JVM dependency's public API, prefer `cellar` when it is available and the smallest reliable approach. Use this Maven cache workflow when JAR, source JAR, POM, metadata, or dependency-graph inspection is more suitable.
- Choose a stable library key, such as `cats-effect`, and use `$HOME/.agents/librarian/maven/cats-effect/` as Maven's persistent local repository. Inspect the exact coordinate's files there before resolving it. Do not use the default `~/.m2/repository` as the download destination.
- For one direct artifact, use Maven with `-Dtransitive=false`; do not create a synthetic project. For a transitive graph or effective resolution, create a request directory below the library cache, write a POM there, and invoke Maven with `-f <absolute-pom-path>`.
- Keep request POMs and graph output below `$HOME/.agents/librarian/maven/<library-key>/requests/<request-key>/`. Reuse an existing request with the same coordinate and repository definitions instead of resolving it again.

For example, to inspect the Cats-Effect 3.7.0 source JAR:

```sh
mkdir -p "$HOME/.agents/librarian/maven/cats-effect"
mvn -B dependency:get -Dartifact=org.typelevel:cats-effect_3:3.7.0:jar:sources -Dtransitive=false "-Dmaven.repo.local=$HOME/.agents/librarian/maven/cats-effect"
jar tf "$HOME/.agents/librarian/maven/cats-effect/org/typelevel/cats-effect_3/3.7.0/cats-effect_3-3.7.0-sources.jar"
```

If the exact JAR already exists, skip `mvn` and inspect it directly. Use the same cache for the binary JAR, POM, and `javadoc` classifier. If `mvn -v` fails, report that Maven is unavailable and do not attempt this workflow.

For a graph, use a persistent request directory rather than a disposable task directory:

```sh
mkdir -p "$HOME/.agents/librarian/maven/cats-effect/requests/3.7.0-graph"
cat > "$HOME/.agents/librarian/maven/cats-effect/requests/3.7.0-graph/pom.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 https://maven.apache.org/xsd/maven-4.0.0.xsd">
  <modelVersion>4.0.0</modelVersion>
  <groupId>agents.research</groupId>
  <artifactId>cats-effect-evidence</artifactId>
  <version>1.0.0</version>
  <dependencies>
    <dependency>
      <groupId>org.typelevel</groupId>
      <artifactId>cats-effect_3</artifactId>
      <version>3.7.0</version>
    </dependency>
  </dependencies>
</project>
EOF
mvn -B -q -f "$HOME/.agents/librarian/maven/cats-effect/requests/3.7.0-graph/pom.xml" dependency:tree -Dverbose -DoutputType=text "-DoutputFile=$HOME/.agents/librarian/maven/cats-effect/requests/3.7.0-graph/tree.txt" "-Dmaven.repo.local=$HOME/.agents/librarian/maven/cats-effect"
```

Inspect the persistent output and resolved files before responding.

## Reporting

Cite URLs, artifact coordinates, Git refs, and repository-relative paths/line ranges. Separate verified facts from inference and state uncertainty.
