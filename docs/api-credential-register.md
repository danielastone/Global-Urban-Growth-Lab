# API credential register

## Purpose

This register governs credentials used to acquire external research data. It records credential provenance, ownership, status, scope, and storage controls **without ever recording the credential value itself**.

A valid file hash proves artifact identity after acquisition; it does not prove that the source was accessed through an authorized, attributable credential. Credential provenance is therefore part of the project's data-provenance chain.

## Fail-closed rule

An acquisition path that requires authentication must remain `MANUAL BLOCK` unless its credential has a register entry with verified provider/account provenance, authorized purpose, storage method, and current status.

The existence of an environment variable or a working credential is not sufficient evidence of authorization or provenance.

Unknown, unattributable, leaked, or unexpectedly supplied credentials must not be used for production acquisition.

## Prohibited content

Never commit API keys, tokens, passwords, client secrets, private keys, recovery codes, partial secret values intended to identify a credential, or secret-bearing URLs/logs/screenshots/fixtures/issues/test output.

Store secrets only in an approved local secret store, environment injection mechanism, or repository/CI secret facility. This register stores metadata only.

## Status vocabulary

- `not_required` — service is accessed without a credential.
- `not_obtained` — credential is required but no credential has been obtained/evidenced.
- `active` — credential provenance and storage are verified and use is authorized.
- `expired` — provider no longer accepts the credential because its validity ended.
- `revoked` — credential has deliberately been invalidated.
- `unknown` — existence, ownership, provenance, or validity cannot be established. Fail closed.

## Register

| credential_id | provider | API/service | required | status | owner/account provenance | provenance verified | storage method | environment variable | scope | billing enabled | used in production | last verified use | repository exposure check | review due | notes |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| census_api_key | U.S. Census Bureau | Census Data API — 2010 SF1 / 2020 PL place acquisition | yes | `not_obtained` | No credential/account evidenced in repository or project execution record | no | Not established | `CENSUS_API_KEY` | Census Data API queries | Not established | no | Never evidenced | Current source contains no literal key; empirical Census inputs/results are not registered | Before first acquisition | `scripts/fetch_us_census_place_pilot.py` requires this variable. PR #81 documented the empirical run as blocked pending a locally exported key. |

## Required acquisition chain

For authenticated sources, preserve:

`Source -> API/service -> credential requirement -> credential record -> acquisition event -> raw artifact -> SHA-256 -> transformation -> analytical result`

The credential node contains metadata only. The secret itself must remain outside Git and outside research artifacts.

## Before first use

Before changing a credential from `not_obtained` or `unknown` to `active`, document:

1. authoritative provider and exact service;
2. account or organizational owner responsible for the credential;
3. how the credential was obtained from the provider;
4. authorized research purpose;
5. credential scope/permissions and any billing exposure;
6. approved storage mechanism;
7. environment-variable or secret identifier used by code;
8. repository-history/exposure check;
9. verification date and reviewer;
10. rotation, expiration, or periodic review requirement.

Do not record the secret value during this process.

## Acquisition-event requirement

When an authenticated acquisition actually occurs, its provenance record should identify the `credential_id` used, not the credential value. The event should also record the authoritative endpoint, retrieval timestamp, final resolved host where relevant, response/file identity, byte count, and SHA-256 before the input is promoted into the registered research pipeline.

## Incident rule

If a secret is discovered in Git history, logs, issues, artifacts, or other project material:

1. stop using it;
2. revoke/rotate it at the provider;
3. mark the register entry `revoked`;
4. document the exposure without reproducing the secret;
5. remove accessible secret-bearing artifacts where appropriate;
6. verify the replacement credential before returning the acquisition path to production.
