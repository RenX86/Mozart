# Mozart Bot - Multi-Platform Music Support

## Quick Test Guide

### Test 1: YouTube Search (Primary)
```
/play never gonna give you up
```
Expected: Should find on YouTube first

### Test 2: SoundCloud URL
```
/play https://soundcloud.com/artist/track
```
Expected: Direct SoundCloud playback

### Test 3: Fallback Test
```
/play obscure indie song name
```
Expected: Try YouTube → SoundCloud → JioSaavn → Bandcamp

### Test 4: JioSaavn (Indian Music)
```
/play arijit singh songs
```
Expected: Should work on YouTube or JioSaavn

### Test 5: Bandcamp
```
/play https://bandcamp.com/track/...
```
Expected: Direct Bandcamp playback

## Logs to Watch For

```
Trying YouTube for query: song name
✓ Found on YouTube: Song Title
```

Or if YouTube fails:
```
Trying YouTube for query: song name
✗ YouTube failed: Sign in to confirm...
Trying SoundCloud for query: song name
✓ Found on SoundCloud: Song Title
```

## Next Steps

1. **Test locally** (without cookies first to see fallback)
2. **Export YouTube cookies** (follow deployment guide)
3. **Test locally with cookies**
4. **Deploy to Render**
5. **Test on Render**
