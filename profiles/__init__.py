from profiles.china import aggressive as china_aggressive, adaptive as china_adaptive, cautious as china_cautious
from profiles.us import interventionist as us_interventionist, restrained as us_restrained
from profiles.taiwan import resilient as taiwan_resilient, defeatist as taiwan_defeatist

PROFILES = {
    "china": {"aggressive": china_aggressive, "adaptive": china_adaptive, "cautious": china_cautious},
    "us": {"interventionist": us_interventionist, "restrained": us_restrained},
    "taiwan": {"resilient": taiwan_resilient, "defeatist": taiwan_defeatist},
}
