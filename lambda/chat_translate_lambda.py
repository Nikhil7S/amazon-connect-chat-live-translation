# ------------------------------------------------------------------------------
# MIT License
#
# Copyright (c) 2026
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
#
# ------------------------------------------------------------------------------
# Prototype Notice
#
# This code was developed as a PROTOTYPE for real-time bidirectional chat
# translation using Amazon Connect.
#
# It is provided for reference, learning, and experimentation purposes.
# Before using this code in production, it should be thoroughly reviewed,
# tested, secured, and optimized according to your organization's standards.
#
# By using this code, you acknowledge that you do so at your own risk.
# ------------------------------------------------------------------------------

import boto3, os
translate = boto3.client('translate')
comprehend = boto3.client('comprehend')  # added Comprehend client
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(os.environ['LANG_TABLE'])

def lambda_handler(event, context):
    content = event['chatContent']['content']
    role = event['chatContent']['participantRole']
    contact_id = event['chatContent']['initialContactId']

    resp = table.get_item(Key={'ContactId': contact_id})
    rec = resp.get('Item', {'ContactId': contact_id, 'agentLang': None, 'customerLang': None})

    # Detect language using Comprehend on first message from each side
    if role == 'CUSTOMER' and rec['customerLang'] is None:
        lang_code = comprehend.detect_dominant_language(Text=content)['Languages'][0]['LanguageCode']
        rec['customerLang'] = lang_code
    if role == 'AGENT' and rec['agentLang'] is None:
        lang_code = comprehend.detect_dominant_language(Text=content)['Languages'][0]['LanguageCode']
        rec['agentLang'] = lang_code
    # Save back to DynamoDB
    table.put_item(Item=rec)

    # Determine translation target
    if role == 'CUSTOMER':
        source_lang = rec['customerLang']; target_lang = rec['agentLang']
    else:
        source_lang = rec['agentLang']; target_lang = rec['customerLang']

    # If target lang unknown or same as source, do nothing
    if not target_lang or source_lang == target_lang:
        return {'status': 'APPROVED'}  # no change

    # Perform translation (auto-detect not needed since we know source, but could use it)
    response = translate.translate_text(
        Text=content,
        SourceLanguageCode=source_lang if source_lang else 'auto',
        TargetLanguageCode=target_lang
    )
    new_text = response['TranslatedText']
    return {
        'status': 'PROCESSED',
        'result': {
            'processedChatContent': {
                'content': new_text,
                'contentType': 'text/plain'
            }
        }
    }