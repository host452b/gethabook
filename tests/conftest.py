"""Shared test fixtures for gethatbook."""
import pytest


LIBGEN_SEARCH_HTML = """
<html><body>
<table width="100%" cellspacing="1" cellpadding="1" rules="rows" class="c" id="table1">
<tr valign="top" bgcolor="#C0C0C0">
  <td>ID</td><td>Author(s)</td><td>Title</td><td>Publisher</td>
  <td>Year</td><td>Pages</td><td>Language</td><td>Size</td>
  <td>Extension</td><td colspan="5">Mirrors</td><td>Edit</td>
</tr>
<tr valign="top">
  <td>12345</td>
  <td>Robert C. Martin</td>
  <td><a id="12345" href="/book/index.php?md5=D41D8CD98F00B204E9800998ECF8427E&amp;id=12345">Clean Code: A Handbook of Agile Software Craftsmanship</a></td>
  <td>Prentice Hall</td>
  <td>2008</td>
  <td>464</td>
  <td>English</td>
  <td>5 Mb</td>
  <td>pdf</td>
  <td><a href="http://library.lol/main/D41D8CD98F00B204E9800998ECF8427E">[1]</a></td>
  <td><a href="http://libgen.li/ads.php?md5=D41D8CD98F00B204E9800998ECF8427E">[2]</a></td>
  <td></td><td></td><td></td>
</tr>
<tr valign="top">
  <td>67890</td>
  <td>Martin Fowler</td>
  <td><a id="67890" href="/book/index.php?md5=A1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4&amp;id=67890">Refactoring: Improving the Design of Existing Code</a></td>
  <td>Addison-Wesley</td>
  <td>2018</td>
  <td>448</td>
  <td>English</td>
  <td>12 Mb</td>
  <td>epub</td>
  <td><a href="http://library.lol/main/A1B2C3D4E5F6A1B2C3D4E5F6A1B2C3D4">[1]</a></td>
  <td></td><td></td><td></td><td></td>
</tr>
</table>
</body></html>
"""

LIBGEN_MIRROR_HTML = """
<html><body>
<div id="download">
  <h2><a href="https://download.library.lol/main/d41d8cd9/Robert%20C.%20Martin%20-%20Clean%20Code.pdf">GET</a></h2>
</div>
</body></html>
"""

LIBGEN_SEARCH_NO_RESULTS_HTML = """
<html><body>
<p>Search string must contain minimum 3 characters.</p>
</body></html>
"""

ANNAS_SEARCH_HTML = """
<html><body>
<div class="mb-4">
  <div class="h-[125] flex">
    <div class="flex-col">
      <a href="/md5/D41D8CD98F00B204E9800998ECF8427E" class="text-lg font-bold">
        Clean Code: A Handbook of Agile Software Craftsmanship
      </a>
      <div class="text-sm text-gray-500">Robert C. Martin</div>
      <div class="text-xs">English, 2008, pdf, 5.0MB, 464 pages</div>
    </div>
  </div>
</div>
<div class="mb-4">
  <div class="h-[125] flex">
    <div class="flex-col">
      <a href="/md5/BBBBBBBBBBBBBBBBBBBBBBBBBBBBBBBB" class="text-lg font-bold">
        The Pragmatic Programmer
      </a>
      <div class="text-sm text-gray-500">David Thomas, Andrew Hunt</div>
      <div class="text-xs">English, 2019, epub, 3.2MB, 352 pages</div>
    </div>
  </div>
</div>
</body></html>
"""

ANNAS_DETAIL_HTML = """
<html><body>
<div class="text-3xl font-bold">Clean Code</div>
<div id="md5-panel-downloads">
  <ul class="list-inside">
    <li><a class="js-download-link" href="http://library.lol/main/D41D8CD98F00B204E9800998ECF8427E">Libgen.li</a></li>
    <li><a class="js-download-link" href="http://library.lol/fiction/D41D8CD98F00B204E9800998ECF8427E">Libgen.rs Fiction</a></li>
  </ul>
</div>
</body></html>
"""
