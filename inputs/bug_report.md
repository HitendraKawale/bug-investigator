# Bug: tier lookup fails for some users after April 5 deploy

## Description
Customer support reports that some newly created users cannot load their billing tier.
Existing users appear unaffected. Issue started after the latest deploy.

## Expected
Tier lookup should return a tier string such as "free", "pro", or "enterprise".

## Actual
For affected users, the request fails and the API returns HTTP 500.

## Environment
- Python 3.11
- service: profile-gateway
- cache enabled
- deploy: 2026-04-05.3

## Hints
- Seems more common for users who have not logged in before
- Existing users often work on retry
- We are not sure whether cache is involved
