Example training-data export
============================

This folder ships with Ascended Barron: GroundTruth OS so you can see what the
"Export" button produces before you generate your own.

As you work, the OS quietly logs your dashboard actions and (when you use a
project terminal) your AI sessions to a LOCAL file on this machine — nothing is
uploaded by the OS. When you press "Prepare Training Data" and then "Export",
those local logs are turned into a clean fine-tuning dataset that you own.

The file in this folder, "example-training-export.jsonl", is a tiny sample of
that output. The real export format is JSONL: one conversation per line, each
line shaped like a chat dataset:

  {"messages": [{"role": "user", "content": "..."},
                {"role": "assistant", "content": "..."}]}

This is the common format for fine-tuning chat models, so you can take the file
you export and feed it to your training pipeline of choice.

Note: the conversations in the sample are made up and contain no personal data.
Your own export is empty until you've done real work and pressed Export.
