#!/usr/bin/env bash
# Fetch the non-bundled cohort datasets into datasets/.
# Sources are public mirrors verified in July 2026; each dataset keeps its
# original license and terms (see datasets/README.md).
set -euo pipefail
cd "$(dirname "$0")/../datasets"

echo "NSL-KDD (train + test)"
curl -sL -o KDDTrain+.txt 'https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTrain%2B.txt'
curl -sL -o KDDTest+.txt  'https://raw.githubusercontent.com/defcom17/NSL_KDD/master/KDDTest%2B.txt'

echo "BATADAL (training 1 and 2)"
curl -sL -O 'https://raw.githubusercontent.com/scy-phy/www.batadal.net/master/data/BATADAL_dataset03.csv'
curl -sL -O 'https://raw.githubusercontent.com/scy-phy/www.batadal.net/master/data/BATADAL_dataset04.csv'

echo "UNSW-NB15 (official partitions, community mirror)"
curl -sL -o UNSW_train.csv 'https://raw.githubusercontent.com/ushukkla/nospammers/master/UNSW_NB15_training-set.csv'
curl -sL -o UNSW_test.csv  'https://raw.githubusercontent.com/ushukkla/nospammers/master/UNSW_NB15_testing-set.csv'

echo "Tennessee Eastman (Braatz distribution, test runs)"
mkdir -p tep && cd tep
for f in d00_te d01_te d02_te d04_te d05_te d06_te d07_te d08_te d10_te d12_te d14_te; do
  curl -sL -O "https://raw.githubusercontent.com/camaramm/tennessee-eastman-profBraatz/master/${f}.dat"
done
cd ..

echo "Synthea 1k-patient CSV sample (full multi-table zip)"
curl -sL -o synthea_sample.zip 'https://raw.githubusercontent.com/synthetichealth/synthea-sample-data/master/downloads/synthea_sample_data_csv_apr2020.zip'
unzip -oq synthea_sample.zip -d synthea

echo "IBM TabFormer card transactions (~278 MB, optional)"
echo "  skipped by default; run with TABFORMER=1 to fetch"
if [ "${TABFORMER:-0}" = "1" ]; then
  curl -L -o tabformer.tgz 'https://media.githubusercontent.com/media/IBM/TabFormer/main/data/credit_card/transactions.tgz'
  tar -xzf tabformer.tgz
fi

echo "done."
