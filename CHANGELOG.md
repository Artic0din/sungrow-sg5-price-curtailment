# Changelog

All notable changes to this project will be documented in this file.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Unreleased]

### Changed
- Issue-backed agent branches now put the issue number first so repository policy can verify the linked issue.

### Added
- CI now validates every Home Assistant YAML file and protects the inverter register, curtailment, restart, and sunset safety contracts with automated tests.
- Wiki auto-update workflow on PR merge
