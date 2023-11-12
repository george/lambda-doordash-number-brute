<h1 align="center"> Doordash Number Brute </h1>

Demonstration on bruteforcing DoorDash account phone numbers using AWS
Lambda functions to bypass CloudFlare WAF ratelimiting, in a race condition-style.

### Introduction

I originally found that you could verify the phone number on a DoorDash
account a few months ago, while researching account checking on DoorDash.

Initially, I created a script using multiprocessing and multithreading
that would check possible phone numbers on an account, however this
led to ratelimiting from an algorithm that I was never able to reverse-engineer,
though I believe it originally ratelimited IP addresses after around 350 requests
per minute, however I was never able to verify this.

I eventually forgot about the project, but decided to remake it using
cloud computing and serverless lambda functions, to help counter the
rate limiting, since AWS' IP pool would be more effective and cheaper
to utilize than purchasing a rotating proxy (though that's still a
very effective solution to bypass the WAF's ratelimiting).

### Features

- Fully bypasses DoorDash's Cloudflare WAF using TLS client, where normal HTTP clients would be flagged instantly.
- Completely serverless using AWS lambda functions
- Reports phone numbers where ratelimiting was detected

The query string accepts an email address, beginning and ending numbers,
and a region. All this information can be obtained through OSINT.
