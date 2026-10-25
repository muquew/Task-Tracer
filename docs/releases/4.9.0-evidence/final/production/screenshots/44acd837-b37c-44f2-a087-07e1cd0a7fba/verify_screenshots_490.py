"""External 4.9.0 screenshot publication proof; inert without --start and accepted candidate selectors."""
from __future__ import annotations

import json
from pathlib import Path
import ssl
import struct
import sys
import traceback
from urllib.error import HTTPError
from urllib.parse import urljoin
from urllib.request import urlopen
import uuid
import zlib

sys.dont_write_bytecode = True
from release_490_common import (AcceptedCandidate, ROOT, SAFE_HEADERS, SITE,
    archive_preparation, base_parser, inherited_proxy, now, require_execution, seal, sha)

SCREENSHOTS = ('screenshots/task-list.png', 'screenshots/task-list-en.png',
               'screenshots/add-task.png', 'screenshots/add-task-en.png')
DIMENSIONS = (1440, 1024)


def png_ihdr(raw):
    if len(raw) < 33 or raw[:8] != b'\x89PNG\r\n\x1a\n':
        raise ValueError('Response is not a PNG with a complete first chunk')
    if struct.unpack('>I', raw[8:12])[0] != 13 or raw[12:16] != b'IHDR':
        raise ValueError('PNG first chunk is not a 13-byte IHDR')
    if zlib.crc32(raw[12:29]) & 0xffffffff != struct.unpack('>I', raw[29:33])[0]:
        raise ValueError('PNG IHDR CRC differs')
    width, height = struct.unpack('>II', raw[16:24])
    return {'width': width, 'height': height, 'ihdr_crc_valid': True}


def run(args):
    candidate = AcceptedCandidate(args)
    inherited_proxy()
    frozen_files = candidate.freeze['source']['files']
    assert all(name in frozen_files for name in SCREENSHOTS), 'All four screenshot sources must be frozen'
    assert len(frozen_files) == 23 and len(candidate.freeze['verification']['files']) == 70, 'Expected the final 93-input 4.9.0 candidate'
    tls = ssl.create_default_context()
    assert tls.check_hostname and tls.verify_mode == ssl.CERT_REQUIRED
    directory = args.output_root / 'screenshots' / str(uuid.uuid4())
    archive_preparation(candidate, directory, __file__)
    (directory / 'assets').mkdir()
    record = {**candidate.record(), 'schema_version': 1, 'run_id': directory.name,
        'started_at': now(), 'finished_at': None, 'status': 'running', 'completed': False,
        'passed': False, 'error': None, 'source_input_count': 23, 'verification_input_count': 70,
        'tls_verification_enabled': True, 'tls_hostname_verification': True,
        'proxy_inherited': True, 'cache_busting_or_custom_headers': False,
        'scope': 'Four real HTTPS screenshots/ responses outside the original 15-response verifier; exact frozen source bytes/SHA, HTTP200/final URL/image/png, PNG IHDR1440x1024. No browser or manual image-inspection claim.',
        'planned': [{'path': name, 'expected_sha256': frozen_files[name]} for name in SCREENSHOTS],
        'responses': [], 'manual_image_inspection': 'pending_parent_review'}
    report_path = directory / 'report.json'
    publish = lambda: candidate.atomic_report(report_path, record)
    publish()
    print('EVIDENCE_DIRECTORY=' + str(directory), flush=True)
    try:
        for relative in SCREENSHOTS:
            candidate.check()
            url = urljoin(SITE, relative)
            item = {'path': relative, 'request_url': url, 'started_at': now(),
                    'expected_sha256': frozen_files[relative], 'passed': False, 'error': None}
            try:
                try:
                    response = urlopen(url, timeout=20, context=tls)
                except HTTPError as error:
                    response = error
                with response:
                    raw = response.read()
                    body_path = 'assets/' + Path(relative).name
                    (directory / body_path).write_bytes(raw)
                    item.update(final_url=response.geturl(), status=response.getcode(),
                        bytes=len(raw), sha256=sha(raw), body_file=body_path,
                        content_type=response.headers.get('Content-Type'),
                        parsed_media_type=response.headers.get_content_type(),
                        headers={key: response.headers.get(key) for key in SAFE_HEADERS
                                 if response.headers.get(key) is not None})
                item['exact_frozen_sha256'] = item['sha256'] == item['expected_sha256']
                item['exact_local_source_bytes'] = raw == (ROOT / relative).read_bytes()
                item['png'] = png_ihdr(raw)
                checks = {
                    'http_200': item['status'] == 200,
                    'exact_final_url': item['final_url'] == url,
                    'image_png': item['parsed_media_type'] == 'image/png',
                    'exact_frozen_sha256': item['exact_frozen_sha256'],
                    'exact_local_source_bytes': item['exact_local_source_bytes'],
                    'dimensions_1440x1024': (item['png']['width'], item['png']['height']) == DIMENSIONS,
                }
                item['checks'] = checks
                if not all(checks.values()):
                    raise AssertionError('Screenshot response failed: ' + ', '.join(key for key, passed in checks.items() if not passed))
                item['passed'] = True
            except Exception as error:
                item.update(error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
            finally:
                item['finished_at'] = now()
                record['responses'].append(item)
                publish()
                print(json.dumps({'path': relative, 'passed': item['passed'], 'status': item.get('status')}), flush=True)
        candidate.finish_identity(record)
        assert len(record['responses']) == 4 and all(item['passed'] for item in record['responses']), 'One or more screenshot responses failed; raw results retained'
        record.update(status='passed', passed=True)
    except BaseException as error:
        record.update(status='failed', passed=False, error=f'{type(error).__name__}: {error}', traceback=traceback.format_exc())
    finally:
        try:
            candidate.finish_identity(record)
        except BaseException as error:
            record.update(status='failed', passed=False, identity_error=f'{type(error).__name__}: {error}')
        record.update(completed=True, finished_at=now())
        publish()
        seal(directory, candidate.atomic_report)
        print(json.dumps({'status': record['status'], 'passed': record['passed'], 'report': str(report_path)}), flush=True)
    return 0 if record['passed'] else 1


def main():
    parser = base_parser(__doc__)
    args = parser.parse_args()
    require_execution(parser, args)
    return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
