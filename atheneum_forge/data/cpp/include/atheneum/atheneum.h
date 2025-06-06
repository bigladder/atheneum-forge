/* Copyright (c) 2019 Big Ladder Software LLC. All rights reserved.
 * See the LICENSE file for additional terms and conditions. */

#pragma once

#include <memory>
#include <functional>
#include <string_view>

#include <atheneum/version.h>

namespace Atheneum
{

class AtheneumPrivate;

class Atheneum
{
  public:
    // If necessary, below are templates for the rule-of-five. Otherwise, prefer rule-of-zero.
    Atheneum();
    Atheneum(const Atheneum&) = default;
    Atheneum(Atheneum&&) = default;
    Atheneum& operator=(const Atheneum&) = default;
    Atheneum& operator=(Atheneum&&) = default;
    //virtual
      ~Atheneum() = default;

    int answer();

  private:
    std::unique_ptr<AtheneumPrivate> atheneum;
};

} // namespace Atheneum
