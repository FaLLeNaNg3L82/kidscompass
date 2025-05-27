# Contributing to KidsCompass

Thank you for your interest in contributing to KidsCompass! We welcome developers of all levels. This guide will help you get started.

---

## KidsCompass Roadmap (English Translation)

This document summarizes the major upcoming tasks and can be tracked/versioned in the Git repository.

**1. Persistence Model**

* Remove JSON files; store all patterns, overrides, and visit status in SQLite.
* Implement a clear DAO interface in `data.py`.
* Migration tool: import existing JSON data into the database.

**2. Reporting Tab**

* Extended PDF layouts (cover page, tables).
* Chart integration directly in the UI (mini-preview).
* Support for multiple chart types (line, bar, heatmap).

**3. Advanced Statistics Queries**

* Wednesday absence reports (filter by weekday).
* Trend analysis over time (e.g., rolling averages).
* Frequency distribution by weekdays vs. weekends.
* Export statistics as CSV/Excel.

**4. Test Coverage**

* Unit tests for all DB functions (`data.py`).
* UI tests (e.g., with `pytest-qt`) for tab interactions.
* Quick integration tests (PDF/chart generation).

**5. Linting & Formatting**

* Configure Black as code formatter.
* Use `isort` for import sorting.
* `flake8` for static linting.
* Pre-commit hook automation.

**6. Workflow & Git Best Practices**

* Setup GitHub Projects / Issues and link them.
* Define a branching model (Git Flow / trunk-based).
* Automate release tagging (CI/CD).

---

## How to Post a GitHub Issue

1. Go to the \[KidsCompass repository on GitHub].
2. Click the **Issues** tab.
3. Click **New issue**.
4. Use the issue template if available; otherwise, provide:

   * **Title:** Short, descriptive summary (e.g., "Add end\_date support to visit patterns").
   * **Description:** Describe the problem, steps to reproduce, expected behavior, and any relevant logs or screenshots.
   * **Environment:** OS, Python version, KidsCompass version.
5. Click **Submit new issue**.

## How to Submit a Pull Request

1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature-name`.
3. Make your changes and commit: `git commit -m "feat: add ..."`.
4. Push to your fork: `git push origin feature/your-feature-name`.
5. Open a pull request against the `main` branch of the upstream repo.
6. Fill in the PR template with a clear description of your changes.

## Sample Forum / Discord Help Request

```markdown
Subject: Seeking Contributors and Guidance for KidsCompass Open Source Project

Hello everyone,

I am the primary maintainer of **KidsCompass**, an open source Python/PySide6 application to manage and visualize child visitation schedules, track attendance, and generate reports.

**What we need:**
- Experienced Python/SQLite developers to advise on database migrations and schema design.
- Contributors interested in enhancing the Reporting and Statistics features (charts, PDF layouts, trend analysis).
- Help setting up CI/CD, linting (Black, isort, flake8), and automated tests (`pytest-qt`).

**Project:** https://github.com/YourUsername/kidscompass

Feel free to comment here or open an issue/discussion on GitHub. Any guidance, code reviews, or small contributions are greatly appreciated!

Thank you!

— Maintainer
```

## Helpful Communities and Links

* **GitHub Discussions:** Enable/participate in the repo’s discussions.
* **Python Discord:** [https://discord.gg/python](https://discord.gg/python)
* **Stack Overflow:** Tag questions with `python` and `pyside6`.
* **r/learnprogramming** on Reddit: [https://reddit.com/r/learnprogramming](https://reddit.com/r/learnprogramming)
* **Gitter**: [https://gitter.im/](https://gitter.im/)
* **GitHub Community Forum:** [https://github.community/](https://github.community/)

---

We look forward to your contributions! 🎉
