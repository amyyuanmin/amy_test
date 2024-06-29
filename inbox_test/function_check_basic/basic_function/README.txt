execute all tests in configure file via parameterize mechanism of pytest
pytest basic_function_test.py --device_type=nvme --cfg=fs_config.txt --fwver=v8 b24 -s --sector=500139360 --mn="MRVL 1098 PART0"

the latest: remove identify check, just get identify info
pytest basic_function_test.py --device_type=nvme --cfg=fs_config.txt -s