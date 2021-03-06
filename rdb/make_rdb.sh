#!/bin/bash

OOoPath=/usr/lib/libreoffice
Path=$(dirname "${0}")

rm -f ${Path}/types.rdb

${Path}/merge_rdb.sh ${OOoPath} com/sun/star/auth/XRestKeyMap
${Path}/merge_rdb.sh ${OOoPath} com/sun/star/auth/OAuth2Request
${Path}/merge_rdb.sh ${OOoPath} com/sun/star/auth/XInteractionUserName
${Path}/merge_rdb.sh ${OOoPath} com/sun/star/auth/RestRequestTokenType

read -p "Press enter to continue"

if test -f "${Path}/types.rdb"; then
    ${OOoPath}/program/regview ${Path}/types.rdb
    read -p "Press enter to continue"
fi
