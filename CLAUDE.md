# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is the "prism" project - a managed DNS solution. The repository is currently in its initial state with minimal structure.

## Development Status

This appears to be a newly initialized repository with only a basic README.md file. The project structure and build system have not yet been established.

## Getting Started

Since this is a new project, you may need to:
- Determine the technology stack and framework
- Set up the build system and project structure
- Initialize package management and dependencies
- Establish development workflows and testing frameworks

## Current State

- Repository contains only a README.md with project name "prism"
- No build scripts, package managers, or development tools configured yet
- No existing codebase or documentation to reference

## Development Practices

- Each user story requires the following: 
  1. definition of done
  2. testable 
  3. TDD driven
  4. Unit Tests
  5. Acceptance criteria

## Jira Workflow Notes

- When updating a Jira issue using jira:update_issue you need to use ADF (Atlassian Document Format)
- After you finish reviewing a jira ticket and it has passed its review you need to change the status to done.
- Jira workflow: todo -> in progress -> waiting for review -> in review -> done

## Review Process

- Once you have finished a user story you should put it in the "WAITING FOR REVIEW" column for someone to pick it up and do a code and functionality review.

## User Story Review Guidelines

- When reviewing a user story:
  1. Fully understand the contents of the user story
  2. Ensure you can run the code with no errors
  3. Review the code and verify it behaves as expected
  4. Think critically about any potential missing elements
  5. Check the acceptance criteria
  6. Provide feedback only if required
  7. Once verified, move the issue status to "DONE"

## Development Workflow

- Make sure to check in your code into github after each task has been completed.

## User Story Management

- Make sure you always are updating user stories before, during and after doing issues.