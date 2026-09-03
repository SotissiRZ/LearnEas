import re

_E164_RE = re.compile(r"^\+[1-9]\d{7,14}$")

# Indicatifs proposés par le sélecteur frontend. La validation API refuse ainsi
# un préfixe international qui ne fait pas partie du référentiel LearnEas.
KNOWN_DIAL_CODES = (
    '+1', '+1242', '+1246', '+1264', '+1268', '+1345', '+1441', '+1473', '+1664', '+1670', '+1671',
    '+1684', '+1758', '+1767', '+1784', '+1787', '+1809', '+1868', '+1869', '+1876', '+20', '+211',
    '+212', '+213', '+216', '+218', '+220', '+221', '+222', '+223', '+224', '+225', '+226', '+227',
    '+228', '+229', '+230', '+231', '+232', '+233', '+234', '+235', '+236', '+237', '+238', '+239',
    '+240', '+241', '+242', '+243', '+244', '+245', '+246', '+248', '+249', '+250', '+251', '+252',
    '+253', '+254', '+255', '+256', '+257', '+258', '+260', '+261', '+262', '+263', '+264', '+265',
    '+266', '+267', '+268', '+269', '+27', '+290', '+291', '+297', '+298', '+299', '+30', '+31', '+32',
    '+33', '+34', '+350', '+351', '+352', '+353', '+354', '+355', '+356', '+357', '+358', '+359',
    '+36', '+370', '+371', '+372', '+373', '+374', '+375', '+377', '+378', '+380', '+381', '+383',
    '+385', '+386', '+387', '+389', '+39', '+40', '+41', '+420', '+421', '+423', '+43', '+44', '+45',
    '+46', '+47', '+4779', '+48', '+49', '+500', '+501', '+502', '+503', '+504', '+505', '+506',
    '+507', '+508', '+509', '+51', '+52', '+53', '+54', '+55', '+56', '+57', '+58', '+590', '+591',
    '+592', '+593', '+594', '+595', '+596', '+597', '+598', '+60', '+61', '+62', '+63', '+64', '+65',
    '+66', '+670', '+672', '+673', '+674', '+675', '+676', '+677', '+678', '+679', '+680', '+681',
    '+682', '+683', '+685', '+686', '+687', '+688', '+689', '+690', '+691', '+692', '+7', '+76', '+81',
    '+82', '+84', '+850', '+852', '+853', '+855', '+856', '+86', '+880', '+886', '+90', '+91', '+92',
    '+93', '+94', '+960', '+961', '+962', '+963', '+964', '+965', '+966', '+967', '+968', '+971',
    '+972', '+973', '+974', '+975', '+976', '+977', '+98', '+992', '+993', '+994', '+995', '+996',
    '+998',
)


def normalize_e164_phone(value: str, *, required: bool = False) -> str:
    """Normalise un numéro international sans dépendre d'un fournisseur.

    L'UI LearnEas construit désormais le préfixe depuis un sélecteur d'indicatif, mais
    l'API garde une validation stricte pour empêcher les numéros arbitraires.
    """
    value = str(value or "").strip()
    value = re.sub(r"[\s().-]+", "", value)
    if value.startswith("00"):
        value = "+" + value[2:]
    if not value:
        if required:
            raise ValueError("Numéro requis.")
        return ""
    if not value.startswith("+"):
        raise ValueError("Utilisez un indicatif international sélectionné dans la liste LearnEas.")
    if not _E164_RE.match(value):
        raise ValueError("Numéro international invalide. Vérifiez l'indicatif et le numéro national.")
    if not any(value.startswith(prefix) for prefix in KNOWN_DIAL_CODES):
        raise ValueError("Indicatif téléphonique non reconnu. Sélectionnez un indicatif dans la liste LearnEas.")
    return value
