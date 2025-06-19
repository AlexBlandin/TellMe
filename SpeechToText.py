import marimo

__generated_with = "0.13.15"
app = marimo.App()


@app.cell(hide_code=True)
def _(mo):
  mo.md(
    r"""
        # Speech To Text Services - Test
        """
  )


@app.cell
def _():
  import os
  from os import path

  import speech_recognition as sr
  from jiwer import compute_measures
  from pydub import AudioSegment

  return AudioSegment, compute_measures, os, path, sr


@app.cell(hide_code=True)
def _(mo):
  mo.md(
    r"""
        ## Converting to the correct file format

        Requires ffmpeg
        """
  )


@app.cell
def _(path):
  DIRECTORY = path.realpath("recordings")
  TRANSCRIPTS = path.realpath("transcripts")
  return DIRECTORY, TRANSCRIPTS


@app.cell
def _(AudioSegment, DIRECTORY, os, path):
  file_names = []
  for _root, _dirs, _files in os.walk(DIRECTORY):
    for _file in _files:
      file_names.append(_file.split(".")[0] + ".flac")
      _file_location = path.join(DIRECTORY, _file)
      with open(_file_location, "rb") as audio_file:
        _fileToExport = AudioSegment.from_file(audio_file, "m4a")
        _fileToExport.export(DIRECTORY + "\\" + file_names[-1], format="flac", parameters=["-c:a", "flac"])
  return (file_names,)


@app.cell
def _(file_names):
  file_names


@app.cell
def _(DIRECTORY, file_names, sr):
  r = sr.Recognizer()
  googleTTS = []
  sphinxTTS = []
  for _file_name in file_names:
    print("File is: " + _file_name)
    with sr.AudioFile(DIRECTORY + "\\" + _file_name) as _source:
      audio = r.record(_source)
    googleTTS.append(r.recognize_google(audio))
    sphinxTTS.append(r.recognize_sphinx(audio))
    print("\n")
    print("Google Speech Recognition thinks you said " + googleTTS[-1])
    print("\n")
    print("Sphinx thinks you said " + sphinxTTS[-1])
    print("\n")
  return googleTTS, r, sphinxTTS


@app.cell
def _(TRANSCRIPTS, os, path):
  transcripts = []
  for _root, _dirs, _files in os.walk(TRANSCRIPTS):
    for _file in _files:
      _file_location = path.join(TRANSCRIPTS, _file)
      with open(_file_location) as curTranscript:
        transcripts.append(curTranscript.read())
  return (transcripts,)


@app.cell
def _(transcripts):
  import pprint

  pprint.pprint(transcripts)
  return (pprint,)


@app.cell
def _(googleTTS, pprint):
  pprint.pprint(googleTTS)


@app.cell
def _():
  with open("My First Project-da3d8912e85c.json") as json_credentials:
    credentials = json_credentials.read()
  return (credentials,)


@app.cell
def _(AudioSegment, DIRECTORY, credentials, file_names, path, r, sr):
  googleCloudTTS = []
  firstmin = 60 * 1000
  for _file_name in file_names:
    _fileToExport = AudioSegment.from_file(path.join(DIRECTORY, _file_name), "flac")
    firstminAudio = _fileToExport[:firstmin]
    lastminAudio = _fileToExport[firstmin:]
    firstminAudio.export(
      path.join(DIRECTORY, _file_name.split(".")[0] + "-part1.flac"), format="flac", parameters=["-c:a", "flac"]
    )
    lastminAudio.export(
      path.join(DIRECTORY, _file_name.split(".")[0] + "-part2.flac"), format="flac", parameters=["-c:a", "flac"]
    )
    print("File is: " + _file_name)
    with sr.AudioFile(path.join(DIRECTORY, _file_name.split(".")[0] + "-part1.flac")) as _source:
      audio1 = r.record(_source)
    with sr.AudioFile(path.join(DIRECTORY, _file_name.split(".")[0] + "-part2.flac")) as _source:
      audio2 = r.record(_source)
    googleCloudResponse = r.recognize_google_cloud(audio1, credentials_json=credentials)
    googleCloudResponse += r.recognize_google_cloud(audio2, credentials_json=credentials)
    googleCloudTTS.append(googleCloudResponse)
    print("\n")
    print("Google Cloud Speech To Text thinks you said " + googleCloudTTS[-1])
    print("\n")
  return (googleCloudTTS,)


@app.cell
def _(googleCloudTTS):
  googleCloudTTS


@app.cell
def _(
  compute_measures,
  googleCloudTTS,
  googleTTS,
  pprint,
  sphinxTTS,
  transcripts,
):
  for i in range(len(transcripts)):
    truth = transcripts[i]
    googleCloudTranscript = googleCloudTTS[i]
    googleTranscript = googleTTS[i]
    sphinxTranscript = sphinxTTS[i]
    _googleCloudMeasures = compute_measures(truth, googleCloudTranscript)
    _googleMeasures = compute_measures(truth, googleTranscript)
    _sphinxMeasures = compute_measures(truth, sphinxTranscript)
    pprint.pprint(_googleCloudMeasures)
    pprint.pprint(_googleMeasures)
    pprint.pprint(_sphinxMeasures)


@app.cell
def _(
  compute_measures,
  googleCloudTTS,
  googleTTS,
  pprint,
  sphinxTTS,
  transcripts,
):
  _googleCloudMeasures = compute_measures(transcripts, googleCloudTTS)
  _googleMeasures = compute_measures(transcripts, googleTTS)
  _sphinxMeasures = compute_measures(transcripts, sphinxTTS)
  pprint.pprint(_googleCloudMeasures)
  pprint.pprint(_googleMeasures)
  pprint.pprint(_sphinxMeasures)


@app.cell
def _():
  import marimo as mo

  return (mo,)


if __name__ == "__main__":
  app.run()
