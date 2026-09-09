## Configuration

Create a `.env` file with the credentials for the providers used by the app:

```env
SARVAM_API_KEY=your_sarvam_api_key
RIME_API_KEY=your_rime_api_key
```

The agent uses Sarvam's `sarvam-105b-conversations` model by default. Override
`SARVAM_MODEL` or `SARVAM_API_URL` when needed.
