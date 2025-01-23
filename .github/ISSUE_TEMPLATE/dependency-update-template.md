---
name: Notify Regular Dependency Template
about: Regular dependency update for the Notification-Utils repo
title: 'Utils - Regular Update for Dependencies'
labels: Notify, QA
assignees: ''
---


## User Story - Business Need

See outstanding dependabot[PRs](https://github.com/department-of-veterans-affairs/notification-utils/pulls).

- [ ] Ticket is understood, and QA has been contacted (if the ticket has a QA label).


### User Story(ies)

**As a**   VANotify engineer
**I want**  to stay on top of dependency updates
**So that** the codebase is up-to-date and secure.

### Additional Info and Resources

## Engineering Checklist

- [ ] Review these [PRs](https://github.com/department-of-veterans-affairs/notification-utils/pulls) to see which files need to change (do not modify those PRs; do not assume any specific file)
- [ ] [setup.py](https://github.com/department-of-veterans-affairs/notification-utils/blob/main/setup.py) seems to be out of scope for dependabot, review it and ensure that the versions there match the versions in the requirements_for_test file 
- [ ] Modify the files to update to the latest versions
- [ ] Unit tests pass
- [ ] Modify the Notification API pyproject.toml file to pull in this branch/sha and then deploy that API branch
- [ ] Ticket is created for specific dependency if any given dependency isn't working correctly

## Acceptance Criteria

- [ ] Dependencies are updated 
- [ ] Unit tests and Notification API regression passes
- [ ] This work is added to the sprint review slide deck (key win bullet point and demo slide)


## QA Considerations
- [ ] Validate that dependabot issues are closed after merge

## Out of Scope
<!-- Include any out of scope work here.  -->
